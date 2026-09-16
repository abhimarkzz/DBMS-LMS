from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import enum
import uuid

Base = declarative_base()

class MaterialType(str, enum.Enum):
    PDF = 'PDF'
    LECTURE_NOTES = 'LECTURE_NOTES'
    PRESENTATION = 'PRESENTATION'
    VIDEO = 'VIDEO'
    DOCUMENT = 'DOCUMENT'
    OTHER = 'OTHER'

class MaterialStatus(str, enum.Enum):
    UPLOADING = 'UPLOADING'
    PROCESSING = 'PROCESSING'
    READY = 'READY'
    FAILED = 'FAILED'

class ContentType(str, enum.Enum):
    PDF = 'PDF'
    LECTURE = 'LECTURE'
    NOTE = 'NOTE'
    STUDY_MATERIAL = 'STUDY_MATERIAL'

class CourseMaterial(Base):
    __tablename__ = "course_materials"

    material_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_id = Column(UUID(as_uuid=True), nullable=False)
    uploaded_by = Column(UUID(as_uuid=True), nullable=False)
    title = Column(String(255), nullable=False)
    material_type = Column(Enum(MaterialType, name="material_type"), nullable=False)
    content_type = Column(Enum(ContentType, name="content_type"), nullable=False, default=ContentType.STUDY_MATERIAL)
    file_name = Column(String(255), nullable=False)
    storage_name = Column(String(255), nullable=False)
    file_url = Column(String(500), nullable=False)
    file_size_bytes = Column(BigInteger)
    mime_type = Column(String(100))
    checksum = Column(String(64))
    description = Column(Text)
    total_chunks = Column(Integer)
    status = Column(Enum(MaterialStatus, name="material_status"), nullable=False, default=MaterialStatus.UPLOADING)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    processed_at = Column(DateTime(timezone=True))
    
    chunks = relationship("MaterialChunk", back_populates="material", cascade="all, delete-orphan")


class MaterialChunk(Base):
    __tablename__ = "material_chunks"

    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_id = Column(UUID(as_uuid=True), ForeignKey("course_materials.material_id", ondelete="CASCADE"), nullable=False)
    chunk_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    page_number = Column(Integer)
    token_count = Column(Integer)
    
    embedding = Column(Vector(384))
    
    embedding_model = Column(String(100))
    embedding_provider = Column(String(50))
    embedding_dimension = Column(Integer)
    chunk_metadata = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    material = relationship("CourseMaterial", back_populates="chunks")
