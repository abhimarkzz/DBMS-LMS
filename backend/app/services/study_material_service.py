import logging
import os
from typing import List, Dict, Any, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.sql_models import Course, StudyMaterial, User
from app.repositories.course_repo import CourseRepository
from app.repositories.note_chunk_repo import NoteChunkRepository
from app.services.ai_search_service import AISearchService
from app.services.document_parser_service import DocumentParserService, SUPPORTED_EXTENSIONS
from app.services.file_storage_service import FileStorageService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class StudyMaterialService:
    def __init__(self, db: Session):
        self.db = db
        self.course_repo = CourseRepository(db)
        self.chunk_repo = NoteChunkRepository(db)
        self.ai_service = AISearchService(db)

    def _verify_course_ownership(self, course: Course, user: User):
        """Ensure user is an ADMIN or the assigned teacher for this course."""
        if user.role.name != "ADMIN" and course.teacher_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to manage study materials for this course."
            )

    async def upload_file_material(
        self,
        course_id: int,
        filename: str,
        file_bytes: bytes,
        user: User,
        custom_title: Optional[str] = None
    ) -> StudyMaterial:
        """
        Process uploaded file:
        1. Check course ownership
        2. Validate format and non-empty content
        3. Check duplicate upload
        4. Extract and clean text (PDF, DOCX, PPTX, TXT, MD)
        5. Store binary blob in MongoDB
        6. Store metadata and extracted content in PostgreSQL
        7. Chunk and embed using pgvector
        8. Return StudyMaterial model
        """
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        self._verify_course_ownership(course, user)

        # Validate empty file
        if not file_bytes or len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty (0 bytes)."
            )

        # Validate format
        _, ext = os.path.splitext(filename.lower())
        if ext not in SUPPORTED_EXTENSIONS:
            supported = ", ".join(SUPPORTED_EXTENSIONS.values())
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format '{ext}'. Supported formats: {supported}."
            )

        # Check duplicate filename in this course
        existing = self.course_repo.find_material_by_filename(course_id, filename)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A study material with filename '{filename}' already exists for this course."
            )

        title = custom_title.strip() if custom_title and custom_title.strip() else os.path.splitext(filename)[0]

        # Extract text using lightweight parsers
        parsed_text = ""
        file_type = SUPPORTED_EXTENSIONS[ext]
        parse_error = None
        try:
            parsed_text, file_type = DocumentParserService.parse_document(filename, file_bytes)
        except ValueError as ve:
            parse_error = str(ve)
            logger.warning(f"Document parsing error for {filename}: {parse_error}")

        # Store binary file in MongoDB
        content_type_map = {
            "PDF": "application/pdf",
            "DOCX": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "PPTX": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "TXT": "text/plain",
            "MD": "text/markdown"
        }
        content_type = content_type_map.get(file_type, "application/octet-stream")
        storage_id = FileStorageService.store_file(
            course_id=course_id,
            filename=filename,
            content_type=content_type,
            data=file_bytes,
            uploaded_by=user.id
        )

        initial_status = "FAILED" if parse_error else "PROCESSING"
        material = self.course_repo.add_study_material(
            course_id=course_id,
            title=title,
            content=parsed_text if parsed_text else "",
            material_type=file_type,
            original_filename=filename,
            file_type=file_type,
            file_size=len(file_bytes),
            file_storage_id=storage_id,
            file_url=f"/api/courses/{course_id}/materials/download",
            uploaded_by=user.id,
            status=initial_status,
            chunk_count=0,
            error_message=parse_error
        )

        # If parsing succeeded, perform chunking and vector embedding into pgvector
        if not parse_error and parsed_text:
            try:
                chunk_count = await self.ai_service.index_study_material(
                    material_id=material.id,
                    course_id=course_id,
                    content=parsed_text,
                    metadata={"original_filename": filename, "file_type": file_type}
                )
                material = self.course_repo.update_study_material_status(
                    material_id=material.id,
                    status="INDEXED",
                    chunk_count=chunk_count,
                    error_message=None
                )
                try:
                    await NotificationService.create_notification(
                        user_id=user.id,
                        title=f"Study Material Indexed: {material.title}",
                        message=f"'{material.title}' was successfully processed into {chunk_count} vector chunks and is now searchable.",
                        notif_type="MATERIAL_INDEXED",
                        metadata={"material_id": material.id, "course_id": course_id, "chunk_count": chunk_count, "target_tab": "materials"}
                    )
                except Exception as n_err:
                    logger.warning(f"Notification error on indexing: {n_err}")
            except Exception as e:
                logger.error(f"Vector indexing failed for material {material.id}: {e}", exc_info=True)
                material = self.course_repo.update_study_material_status(
                    material_id=material.id,
                    status="FAILED",
                    error_message=f"Indexing failed: {str(e)}"
                )

        return material

    async def add_manual_note(
        self,
        course_id: int,
        title: str,
        content: str,
        user: User,
        material_type: str = "NOTES"
    ) -> StudyMaterial:
        """Manual text entry alternative."""
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        self._verify_course_ownership(course, user)

        cleaned_text = DocumentParserService.clean_text(content)
        if not cleaned_text or len(cleaned_text) < 5:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Note content is too short.")

        material = self.course_repo.add_study_material(
            course_id=course_id,
            title=title.strip(),
            content=cleaned_text,
            material_type=material_type,
            file_type="TEXT",
            file_size=len(cleaned_text.encode('utf-8')),
            uploaded_by=user.id,
            status="INDEXED",
            chunk_count=0
        )

        try:
            chunk_count = await self.ai_service.index_study_material(
                material_id=material.id,
                course_id=course_id,
                content=cleaned_text,
                metadata={"title": title, "file_type": "TEXT"}
            )
            material = self.course_repo.update_study_material_status(
                material_id=material.id,
                status="INDEXED",
                chunk_count=chunk_count
            )
            try:
                await NotificationService.create_notification(
                    user_id=user.id,
                    title=f"Note Indexed: {material.title}",
                    message=f"'{material.title}' was successfully embedded into {chunk_count} vector chunks and is now searchable.",
                    notif_type="MATERIAL_INDEXED",
                    metadata={"material_id": material.id, "course_id": course_id, "chunk_count": chunk_count, "target_tab": "materials"}
                )
            except Exception as n_err:
                logger.warning(f"Notification error on indexing: {n_err}")
        except Exception as e:
            logger.warning(f"Indexing manual note failed: {e}")
            material = self.course_repo.update_study_material_status(
                material_id=material.id,
                status="FAILED",
                error_message=f"Indexing failed: {str(e)}"
            )

        return material

    async def reindex_material(self, course_id: int, material_id: int, user: User) -> StudyMaterial:
        """Re-extract and re-index an existing study material into pgvector."""
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        self._verify_course_ownership(course, user)

        material = self.course_repo.get_study_material(material_id)
        if not material or material.course_id != course_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study material not found")

        # Delete existing chunks
        self.chunk_repo.delete_chunks_by_material(material_id)

        # If content is empty but storage_id exists, try re-parsing from MongoDB
        content_to_index = material.content
        if (not content_to_index or not content_to_index.strip()) and material.file_storage_id:
            file_doc = FileStorageService.get_file(material.file_storage_id)
            if file_doc and file_doc.get("data"):
                try:
                    content_to_index, _ = DocumentParserService.parse_document(
                        material.original_filename or "document",
                        file_doc["data"]
                    )
                    material.content = content_to_index
                except Exception as ex:
                    material = self.course_repo.update_study_material_status(
                        material_id=material.id,
                        status="FAILED",
                        chunk_count=0,
                        error_message=f"Re-indexing parsing failed: {str(ex)}"
                    )
                    return material

        if not content_to_index or not content_to_index.strip():
            material = self.course_repo.update_study_material_status(
                material_id=material.id,
                status="FAILED",
                chunk_count=0,
                error_message="Cannot re-index empty material text."
            )
            return material

        # Re-index
        try:
            chunk_count = await self.ai_service.index_study_material(
                material_id=material.id,
                course_id=course_id,
                content=content_to_index,
                metadata={"original_filename": material.original_filename, "file_type": material.file_type}
            )
            material = self.course_repo.update_study_material_status(
                material_id=material.id,
                status="INDEXED",
                chunk_count=chunk_count,
                error_message=None,
                content=content_to_index
            )
        except Exception as e:
            material = self.course_repo.update_study_material_status(
                material_id=material.id,
                status="FAILED",
                error_message=f"Re-indexing failed: {str(e)}"
            )

        return material

    def delete_material(self, course_id: int, material_id: int, user: User) -> bool:
        """Delete study material, vector chunks, and raw file."""
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        self._verify_course_ownership(course, user)

        material = self.course_repo.get_study_material(material_id)
        if not material or material.course_id != course_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study material not found")

        # 1. Delete vector chunks
        self.chunk_repo.delete_chunks_by_material(material_id)

        # 2. Delete raw file from MongoDB
        if material.file_storage_id:
            FileStorageService.delete_file(material.file_storage_id)

        # 3. Delete SQL record
        return self.course_repo.delete_study_material(material_id)

    def get_material_file(self, course_id: int, material_id: int, user: User) -> Tuple[str, str, bytes]:
        """Fetch raw binary file for download/viewing."""
        course = self.course_repo.get_course_by_id(course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        # Permission: user must be enrolled student, course teacher, or admin
        is_teacher_or_admin = (user.role.name == "ADMIN" or course.teacher_id == user.id)
        is_enrolled = self.course_repo.is_student_enrolled(user.id, course_id)

        if not is_teacher_or_admin and not is_enrolled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be enrolled in this course to download study materials."
            )

        material = self.course_repo.get_study_material(material_id)
        if not material or material.course_id != course_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study material not found")

        if not material.file_storage_id:
            # Fallback for text notes: generate text/markdown or text/plain on the fly
            content_bytes = (material.content or "").encode("utf-8")
            is_md = (
                (material.material_type and material.material_type.upper() == "MD")
                or material.title.lower().endswith(".md")
            )
            ext = ".md" if is_md else ".txt"
            content_type = "text/markdown" if is_md else "text/plain"
            filename = material.title if material.title.lower().endswith(ext) else f"{material.title}{ext}"
            return filename, content_type, content_bytes

        file_doc = FileStorageService.get_file(material.file_storage_id)
        if not file_doc or not file_doc.get("data"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File content not found in storage.")

        filename = file_doc.get("filename") or material.original_filename or f"{material.title}.bin"
        content_type = file_doc.get("content_type")

        # Fallback or resolve generic octet-stream MIME types
        if not content_type or content_type == "application/octet-stream":
            _, ext = os.path.splitext(filename.lower())
            mime_map = {
                ".pdf": "application/pdf",
                ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
                ".txt": "text/plain",
                ".md": "text/markdown",
            }
            content_type = mime_map.get(ext, "application/octet-stream")

        return filename, content_type, file_doc["data"]
