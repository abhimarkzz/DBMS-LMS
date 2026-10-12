import asyncio
import logging
import json
from datetime import datetime, timedelta
from app.database.postgres import SessionLocal
from app.models.sql_models import Course, Enrollment, StudyMaterial, Assignment, Submission, Result, User, Role
from app.services.ai_search_service import AISearchService
from app.services.notification_service import NotificationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

COURSES_SPEC = [
    {
        "code": "CS201",
        "title": "Data Structures & Algorithms (DSA)",
        "description": "Fundamental data structures and algorithmic design paradigms: balanced trees, heaps, graph traversals, greedy strategies, and dynamic programming.",
        "syllabus": "Unit 1: Asymptotic Complexity & Linear Structures (LinkedLists, Stacks, Queues)\nUnit 2: Non-Linear Structures (AVL Trees, Red-Black Trees, Heaps)\nUnit 3: Graph Algorithms (Dijkstra, Bellman-Ford, BFS/DFS, Tarjan SCC)\nUnit 4: Dynamic Programming & Branch-and-Bound",
        "department": "Computer Science & Engineering",
        "credits": 4,
        "level": "Undergraduate Core",
        "teacher_email": "prof.alan@univ.edu",
        "materials": [
            {
                "title": "Lecture 3: Graph Shortest Path Algorithms & Dijkstra Invariant",
                "content": (
                    "Dijkstra's algorithm finds the shortest path from a single source vertex to all other vertices in a weighted graph with non-negative edge weights. "
                    "It maintains a priority queue of unvisited vertices ordered by their tentative distance from the source. At each step, the vertex with the minimum tentative "
                    "distance is extracted, and all its outgoing edges are relaxed. If a negative edge weight exists, Bellman-Ford or Johnson's algorithm must be used instead. "
                    "Using a Fibonacci Heap, Dijkstra's running time is optimized to O(E + V log V), while a standard binary min-heap achieves O((V + E) log V)."
                )
            },
            {
                "title": "Lecture 7: Dynamic Programming: Optimal Substructure & Memoization",
                "content": (
                    "Dynamic programming solves complex problems by breaking them down into simpler subproblems and storing intermediate results to avoid redundant calculations. "
                    "A problem is suitable for dynamic programming if it exhibits two key properties: Optimal Substructure and Overlapping Subproblems. "
                    "Two principal approaches exist: Top-down with memoization (recursive caching) and Bottom-up tabulation (iterative table construction). "
                    "Classic examples include the 0/1 Knapsack problem, Longest Common Subsequence (LCS), and Matrix Chain Multiplication."
                )
            }
        ],
        "assignments": [
            {
                "title": "Assignment 1: Graph Traversal & Dijkstra Implementation",
                "desc": "Implement Dijkstra's shortest path algorithm using a Min-Heap priority queue in Python/C++ and evaluate complexity on sparse vs dense graphs.",
                "max_score": 100.0,
                "assessment_type": "DESCRIPTIVE"
            },
            {
                "title": "Quiz 1: Algorithmic Complexity & Master Theorem",
                "desc": "Multiple choice questions assessing Big-O notation, recurrence relations, and tree balance invariants.",
                "max_score": 100.0,
                "assessment_type": "MCQ",
                "mcq_config": {
                    "questions": [
                        {
                            "id": "q1",
                            "question": "What is the worst-case time complexity of lookup in a balanced AVL tree with N elements?",
                            "options": ["O(1)", "O(log N)", "O(N)", "O(N log N)"],
                            "correct_answer": "O(log N)"
                        },
                        {
                            "id": "q2",
                            "question": "Which algorithmic paradigm does Dijkstra's shortest path algorithm utilize?",
                            "options": ["Dynamic Programming", "Greedy Approach", "Divide and Conquer", "Backtracking"],
                            "correct_answer": "Greedy Approach"
                        }
                    ]
                }
            }
        ]
    },
    {
        "code": "CS301",
        "title": "Operating Systems & Kernel Architecture (OS)",
        "description": "Process scheduling, thread synchronization, deadlocks, virtual memory management, demand paging, and Linux VFS kernel internals.",
        "syllabus": "Unit 1: Process Lifecycle, Context Switching, & Inter-Process Communication (IPC)\nUnit 2: Threading, Mutexes, Semaphores & Deadlock Avoidance (Banker's Algorithm)\nUnit 3: Virtual Memory, Page Tables, TLB & Replacement Policies (LRU, Clock)\nUnit 4: File Systems, Inodes, Virtual File System (VFS) & Device Drivers",
        "department": "Computer Science & Engineering",
        "credits": 4,
        "level": "Undergraduate Core",
        "teacher_email": "prof.alan@univ.edu",
        "materials": [
            {
                "title": "Module 2: Virtual Memory, Multi-Level Page Tables & TLB Caching",
                "content": (
                    "Virtual memory isolates application address spaces and provides each process with the illusion of contiguous physical memory. "
                    "The Memory Management Unit (MMU) translates virtual addresses into physical addresses using multi-level page tables (such as 4-level paging on x86-64). "
                    "To prevent multiple memory accesses for every translation, the processor caches recent translations in the Translation Lookaside Buffer (TLB). "
                    "When a virtual address is accessed that does not reside in physical RAM, a Page Fault exception is raised, prompting the kernel to swap the page from disk."
                )
            },
            {
                "title": "Module 4: Concurrency Primitives: Mutexes, Spinlocks, & Peterson's Algorithm",
                "content": (
                    "Critical section problems arise when multiple concurrent threads access shared state without mutual exclusion. "
                    "Hardware provides atomic instructions like Test-and-Set and Compare-And-Swap (CAS) to build synchronization primitives. "
                    "A Spinlock busy-waits in a CPU loop and is appropriate for low-latency kernel contexts where sleeping is forbidden (e.g., interrupt handlers). "
                    "In contrast, a Mutex puts contending threads to sleep via OS scheduling queues (such as Linux futex), relinquishing the CPU to other runnable threads."
                )
            }
        ],
        "assignments": [
            {
                "title": "Assignment 1: Multi-Threaded Process Synchronization",
                "desc": "Implement the classic Producer-Consumer and Readers-Writers synchronization protocols using POSIX mutexes and condition variables.",
                "max_score": 100.0,
                "assessment_type": "DESCRIPTIVE"
            }
        ]
    },
    {
        "code": "CS305",
        "title": "Embedded Systems & Real-Time Computing",
        "description": "ARM Cortex-M architecture, bare-metal C programming, GPIO, hardware interrupts, timers, ADC, serial buses (UART/SPI/I2C), and FreeRTOS task scheduling.",
        "syllabus": "Unit 1: ARM Cortex-M Architecture & Memory-Mapped I/O\nUnit 2: Nested Vectored Interrupt Controller (NVIC) & Timers\nUnit 3: Synchronous & Asynchronous Serial Protocols (SPI, I2C, UART)\nUnit 4: Real-Time Operating Systems (FreeRTOS Preemption, Queues, & Semaphores)",
        "department": "Electrical & Computer Engineering",
        "credits": 4,
        "level": "Upper Division",
        "teacher_email": "dr.sarah@univ.edu",
        "materials": [
            {
                "title": "Guide 1: Bare-Metal ARM Interrupts & NVIC Priority Management",
                "content": (
                    "The ARM Cortex-M Nested Vectored Interrupt Controller (NVIC) provides low-latency hardware interrupt handling. "
                    "When a peripheral signals an interrupt request (IRQ), the processor automatically stacks CPU registers (R0-R3, R12, LR, PC, xPSR) "
                    "onto the current stack pointer before jumping to the corresponding address in the Vector Table. "
                    "Interrupt prioritization supports preemption where higher priority IRQs interrupt existing lower priority handlers. "
                    "Interrupt Service Routines (ISRs) must remain concise and delegate heavy computations to background tasks or deferred worker threads."
                )
            },
            {
                "title": "Guide 3: Serial Communication Protocol Comparison: UART vs SPI vs I2C",
                "content": (
                    "Embedded microcontrollers interface with external sensors and peripherals using three foundational serial communication protocols: "
                    "UART is asynchronous, full-duplex, and uses two data lines (TX/RX) without a shared clock, relying on matched baud rates. "
                    "SPI is synchronous, full-duplex, master-slave based, utilizing four wires (MOSI, MISO, SCK, CS) and reaches speeds exceeding 50 MHz. "
                    "I2C is synchronous, half-duplex, multi-master with only two bidirectional open-drain lines (SDA/SCL) and pull-up resistors, supporting 127 addressed devices."
                )
            }
        ],
        "assignments": [
            {
                "title": "Lab 1: FreeRTOS Task Scheduling & Sensor Acquisition",
                "desc": "Design a real-time embedded sensor acquisition pipeline using FreeRTOS with periodic timer triggers and queue-based inter-task data passing.",
                "max_score": 100.0,
                "assessment_type": "DESCRIPTIVE"
            }
        ]
    },
    {
        "code": "LANG101",
        "title": "Japanese Language & Cultural Communication",
        "description": "Comprehensive introduction to Japanese orthography (Hiragana, Katakana, introductory Kanji), syntactic grammar structures, polite honorific speech, and sociocultural context.",
        "syllabus": "Unit 1: Phonetics & Syllabaries: Hiragana & Katakana Mastery\nUnit 2: Basic Grammar Structures, Copula 'Desu', & Particles (Wa, Ga, O, Ni, De)\nUnit 3: Verb Conjugations (Present, Past, Negative) & Te-Form Connections\nUnit 4: Kanji Ideographs, Everyday Dialogues & Business Etiquette (Keigo)",
        "department": "Modern Languages & International Studies",
        "credits": 3,
        "level": "Introductory Humanities",
        "teacher_email": "dr.sarah@univ.edu",
        "materials": [
            {
                "title": "Unit 1: The Japanese Writing System & Particle Mechanics",
                "content": (
                    "The Japanese language employs three writing scripts concurrently: Hiragana (native grammatical particles and inflections), "
                    "Katakana (loan words and onomatopoeia), and Kanji (logographic Chinese characters representing semantic concepts). "
                    "Sentence structure follows Subject-Object-Verb (SOV) order. Grammatical relationships are explicitly demarcated by particles: "
                    "'wa' marks the topical theme of the discourse, 'ga' marks the grammatical subject, 'o' marks the direct object, and 'ni' specifies destination or time."
                )
            },
            {
                "title": "Unit 3: Honorific Language (Keigo) & Cultural Etiquette",
                "content": (
                    "Keigo (polite and respectful language) is essential for expressing social distance, respect, and hierarchy in Japanese society. "
                    "It is subdivided into three categories: Teineigo (polite speech characterized by 'desu' and 'masu' suffixes), "
                    "Sonkeigo (respectful language elevating the actions of the listener or higher-status counterpart), and "
                    "Kenjougo (humble language lowering the actions of oneself to demonstrate modesty and deference)."
                )
            }
        ],
        "assignments": [
            {
                "title": "Quiz 1: Hiragana, Katakana & Grammatical Particle Mastery",
                "desc": "Test your grasp of Japanese grammatical particles, sentence translation, and everyday conversational greetings.",
                "max_score": 100.0,
                "assessment_type": "MCQ",
                "mcq_config": {
                    "questions": [
                        {
                            "id": "q1",
                            "question": "Which particle marks the direct object of a transitive verb in Japanese?",
                            "options": ["は (wa)", "を (o/wo)", "に (ni)", "が (ga)"],
                            "correct_answer": "を (o/wo)"
                        },
                        {
                            "id": "q2",
                            "question": "What is the standard word order in a Japanese sentence?",
                            "options": ["SVO (Subject-Verb-Object)", "SOV (Subject-Object-Verb)", "VSO (Verb-Subject-Object)", "OVS (Object-Verb-Subject)"],
                            "correct_answer": "SOV (Subject-Object-Verb)"
                        }
                    ]
                }
            }
        ]
    },
    {
        "code": "CS401",
        "title": "Machine Learning & Neural Foundations (ML)",
        "description": "Statistical learning theory, convex optimization, linear regression, classification with SVMs, ensemble methods, deep learning architectures, and backpropagation.",
        "syllabus": "Unit 1: Supervised Learning Foundations & Loss Optimization (MSE, Cross-Entropy)\nUnit 2: Regularization Techniques (Ridge L2, Lasso L1, ElasticNet) & Bias-Variance Tradeoff\nUnit 3: Support Vector Machines, Kernel Trick & Ensemble Trees (Random Forests, XGBoost)\nUnit 4: Deep Neural Networks, Multi-Layer Perceptrons & Backpropagation Calculus",
        "department": "Computer Science & Artificial Intelligence",
        "credits": 4,
        "level": "Upper Division / Graduate",
        "teacher_email": "prof.alan@univ.edu",
        "materials": [
            {
                "title": "Lecture 2: Gradient Descent Optimization & Convex Loss Surfaces",
                "content": (
                    "Gradient descent is an iterative optimization algorithm used to minimize differentiable loss functions in machine learning models. "
                    "The model parameters theta are updated in the direction opposite to the gradient of the objective function J(theta): theta := theta - alpha * grad(J(theta)), "
                    "where alpha is the learning rate hyperparameter. In Stochastic Gradient Descent (SGD), the gradient is approximated using a single training sample or mini-batch, "
                    "accelerating computation on large datasets. Advanced optimizers like Adam combine momentum (exponential moving averages of gradients) "
                    "with adaptive learning rates (RMSProp) to navigate saddle points and ill-conditioned ravines."
                )
            },
            {
                "title": "Lecture 5: Neural Network Backpropagation & Computational Graphs",
                "content": (
                    "Backpropagation computes the gradient of the loss function with respect to every weight in a multi-layer neural network using the Chain Rule of calculus. "
                    "In the Forward Pass, input vectors propagate through successive linear transformations followed by non-linear activations (ReLU, GELU, Sigmoid). "
                    "In the Backward Pass, error signals (deltas) are propagated backward from the output layer to compute partial derivatives dL/dW. "
                    "Non-linear activation functions prevent deep networks from collapsing into single linear maps, enabling the representation of complex high-dimensional decision boundaries."
                )
            }
        ],
        "assignments": [
            {
                "title": "Assignment 1: Neural Network from Scratch in NumPy",
                "desc": "Implement a 3-layer neural network with forward propagation, cross-entropy loss, and vectorized analytical backpropagation from scratch without PyTorch/TensorFlow.",
                "max_score": 100.0,
                "assessment_type": "DESCRIPTIVE"
            }
        ]
    }
]

async def run_clean_and_seed():
    db = SessionLocal()
    try:
        logger.info("Cleaning up all legacy/test courses from database...")
        # Delete existing courses (cascades to enrollments, materials, assignments, submissions, results)
        existing_courses = db.query(Course).all()
        for c in existing_courses:
            db.delete(c)
        db.commit()
        logger.info(f"Removed {len(existing_courses)} old courses.")

        # Ensure demo roles and users exist
        from app.services.auth_service import hash_password
        roles = {}
        for role_name, desc in [
            ("ADMIN", "System administrator with complete platform privileges"),
            ("TEACHER", "Course instructor with syllabus, grading, and material control"),
            ("STUDENT", "Enrolled learner with assignment and AI search access")
        ]:
            r = db.query(Role).filter(Role.name == role_name).first()
            if not r:
                r = Role(name=role_name, description=desc)
                db.add(r)
                db.commit()
                db.refresh(r)
            roles[role_name] = r

        default_password = hash_password("Password123!")
        users_data = [
            {"email": "admin@univ.edu", "name": "Dean Victoria Vance", "role": "ADMIN", "pw": hash_password("AdminPass123!")},
            {"email": "prof.alan@univ.edu", "name": "Prof. Alan Turing", "role": "TEACHER", "pw": default_password},
            {"email": "dr.sarah@univ.edu", "name": "Dr. Sarah Connor", "role": "TEACHER", "pw": default_password},
            {"email": "alex@student.univ.edu", "name": "Alex Rivera", "role": "STUDENT", "pw": default_password},
            {"email": "priya@student.univ.edu", "name": "Priya Sharma", "role": "STUDENT", "pw": default_password},
            {"email": "marcus@student.univ.edu", "name": "Marcus Vance", "role": "STUDENT", "pw": default_password},
            {"email": "elena@student.univ.edu", "name": "Elena Rostova", "role": "STUDENT", "pw": default_password},
        ]
        for ud in users_data:
            u = db.query(User).filter(User.email == ud["email"]).first()
            if not u:
                u = User(
                    email=ud["email"],
                    password_hash=ud["pw"],
                    full_name=ud["name"],
                    role_id=roles[ud["role"]].id,
                    is_active=True
                )
                db.add(u)
                db.commit()
                db.refresh(u)
            elif ud["email"] in ["alex@student.univ.edu", "prof.alan@univ.edu", "admin@univ.edu"]:
                # Ensure canonical passwords in case a test modified them
                u.password_hash = ud["pw"]
                db.commit()

        users = {u.email: u for u in db.query(User).all()}
        students = [users[e] for e in ["alex@student.univ.edu", "priya@student.univ.edu", "marcus@student.univ.edu", "elena@student.univ.edu"] if e in users]

        ai_service = AISearchService(db)
        created_courses = {}

        for c_spec in COURSES_SPEC:
            teacher = users.get(c_spec["teacher_email"])
            if not teacher:
                continue

            course = Course(
                code=c_spec["code"],
                title=c_spec["title"],
                description=c_spec["description"],
                syllabus=c_spec["syllabus"],
                department=c_spec["department"],
                credits=c_spec["credits"],
                level=c_spec["level"],
                teacher_id=teacher.id,
                is_published=True,
                status="PUBLISHED"
            )
            db.add(course)
            db.commit()
            db.refresh(course)
            created_courses[c_spec["code"]] = course
            logger.info(f"Created Course: {course.code} - {course.title}")

            # Enroll all students
            for s in students:
                e = Enrollment(student_id=s.id, course_id=course.id, status="ACTIVE")
                db.add(e)
            db.commit()

            # Add study materials and index in pgvector
            for mat_spec in c_spec.get("materials", []):
                sm = StudyMaterial(
                    course_id=course.id,
                    title=mat_spec["title"],
                    content=mat_spec["content"],
                    material_type="NOTES",
                    status="INDEXED"
                )
                db.add(sm)
                db.commit()
                db.refresh(sm)

                # Embed into pgvector
                try:
                    await ai_service.index_study_material(
                        material_id=sm.id,
                        course_id=course.id,
                        content=mat_spec["content"]
                    )
                except Exception as ex:
                    logger.warning(f"Vector embedding notice: {ex}")

            # Add assignments
            for a_spec in c_spec.get("assignments", []):
                cfg_str = json.dumps(a_spec.get("mcq_config")) if "mcq_config" in a_spec else None
                assignment = Assignment(
                    course_id=course.id,
                    title=a_spec["title"],
                    description=a_spec["desc"],
                    max_score=a_spec["max_score"],
                    assessment_type=a_spec["assessment_type"],
                    due_date=datetime.utcnow() + timedelta(days=7),
                    assessment_config=cfg_str,
                    status="PUBLISHED"
                )
                db.add(assignment)
                db.commit()
                db.refresh(assignment)

                # Add sample submissions for student Alex
                if students and a_spec["title"].startswith("Assignment 1"):
                    sub = Submission(
                        assignment_id=assignment.id,
                        student_id=students[0].id,
                        content=f"Detailed analytical report and code solution for {assignment.title}.",
                        status="GRADED",
                        score=95.0,
                        feedback="Outstanding academic rigor, clear mathematical analysis, and complete benchmarks.",
                        graded_at=datetime.utcnow()
                    )
                    db.add(sub)
                    db.commit()

            # Create published course result for student Alex
            if students:
                existing_res = db.query(Result).filter(
                    Result.student_id == students[0].id,
                    Result.course_id == course.id
                ).first()
                if not existing_res:
                    res = Result(
                        student_id=students[0].id,
                        course_id=course.id,
                        total_score=95.0,
                        max_possible=100.0,
                        percentage=95.0,
                        grade="A+",
                        status="PUBLISHED",
                        published_at=datetime.utcnow()
                    )
                    db.add(res)
                    db.commit()
                else:
                    existing_res.total_score = 95.0
                    existing_res.max_possible = 100.0
                    existing_res.percentage = 95.0
                    existing_res.grade = "A+"
                    existing_res.status = "PUBLISHED"
                    db.commit()

            # Post welcome announcement
            try:
                await NotificationService.create_announcement(
                    course_id=course.id,
                    title=f"Welcome to {course.code}: {course.title}",
                    content=f"The Spring 2026 semester syllabus for {course.title} is now active. Please review the first modules and assignments.",
                    author_name=teacher.full_name,
                    course_title=course.title
                )
            except Exception as e:
                logger.warning(f"Announcement notice: {e}")

        logger.info("Successfully cleaned and seeded the 5 academic courses!")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(run_clean_and_seed())
