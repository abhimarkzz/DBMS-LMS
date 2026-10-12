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
        "description": "Rigorous algorithmic design paradigms and core data structures: asymptotic bounds, balanced search trees, priority heaps, shortest path graphs, network flow, and dynamic programming.",
        "syllabus": (
            "Unit 1: Asymptotic Complexity, Amortized Analysis & Master Theorem\n"
            "Unit 2: Balanced Search Trees (AVL, Red-Black Trees, B-Trees) & Binary Heaps\n"
            "Unit 3: Graph Traversal & Shortest Paths (Dijkstra, Bellman-Ford, Floyd-Warshall, A*)\n"
            "Unit 4: Advanced Graphs (Tarjan's SCC, Bridges, Disjoint Sets & Kruskal MST)\n"
            "Unit 5: Dynamic Programming Paradigms (Memoization, Tabulation, Knapsack, LCS)\n"
            "Unit 6: Complexity Classes (P, NP, NP-Complete, Reductions)"
        ),
        "department": "Computer Science & Engineering",
        "credits": 4,
        "level": "Undergraduate Core",
        "teacher_email": "prof.alan@univ.edu",
        "materials": [
            {
                "title": "Lecture 1: Asymptotic Analysis, Master Theorem & Recurrence Relations",
                "content": (
                    "Asymptotic analysis formalizes algorithm execution bounds as input size n approaches infinity. "
                    "Big-O O(g(n)) denotes the asymptotic upper bound, Omega Omega(g(n)) specifies the tight lower bound, and Theta Theta(g(n)) describes the tight sandwich bound. "
                    "The Master Theorem provides a closed-form solution for divide-and-conquer recurrences of the form T(n) = a*T(n/b) + f(n), where a >= 1 and b > 1: "
                    "Case 1: If f(n) = O(n^(log_b(a) - epsilon)), then T(n) = Theta(n^(log_b(a))). "
                    "Case 2: If f(n) = Theta(n^(log_b(a)) * log^k(n)), then T(n) = Theta(n^(log_b(a)) * log^(k+1)(n)). "
                    "Case 3: If f(n) = Omega(n^(log_b(a) + epsilon)) and regularity holds (a*f(n/b) <= c*f(n) for c < 1), then T(n) = Theta(f(n)). "
                    "Amortized analysis guarantees average cost per operation over a worst-case sequence of operations using three formal methods: "
                    "the Aggregate Method, the Accounting (Banker's) Method, and the Potential (Physicist's) Method (Phi(D_i) - Phi(D_0))."
                )
            },
            {
                "title": "Lecture 3: Graph Shortest Path Algorithms & Dijkstra Invariant",
                "content": (
                    "Dijkstra's algorithm finds the shortest path from a single source vertex to all other vertices in a directed or undirected graph with strictly non-negative edge weights (w >= 0). "
                    "The algorithm maintains a priority queue of unvisited vertices keyed by tentative distance dist[v]. At each iteration, the vertex u with minimum tentative distance is extracted and settled. "
                    "The Greedy Choice Invariant guarantees that the settled distance dist[u] equals the absolute minimum shortest path delta(s, u). "
                    "Edge Relaxation: For every outgoing edge (u, v) with weight w(u, v), if dist[u] + w(u, v) < dist[v], tentative distance dist[v] is relaxed and updated in the priority queue. "
                    "Complexity: Using a binary min-heap, Dijkstra executes in O((V + E) log V) time. Using a Fibonacci Heap, decreases-key operations take O(1) amortized time, yielding O(E + V log V). "
                    "Negative Edges: If negative edge weights exist, the greedy invariant is violated. The Bellman-Ford algorithm must be used instead, running in O(V * E) time and detecting negative-weight cycles."
                )
            },
            {
                "title": "Lecture 5: Balanced Search Trees, AVL vs Red-Black Trees & B-Trees",
                "content": (
                    "Self-balancing binary search trees maintain an O(log N) height invariant under dynamic insertions and deletions. "
                    "AVL Trees maintain a strict Balance Factor BF(node) = height(left) - height(right) in {-1, 0, 1}. Violations are restored via O(1) pointer rotations: Left-Left (Single Right), Right-Right (Single Left), Left-Right (Double), and Right-Left (Double). "
                    "Red-Black Trees relax strict balance to reduce rotation frequency during heavy mutations, satisfying five invariants: "
                    "1. Every node is either Red or Black. 2. The root is Black. 3. Every leaf (NIL) is Black. 4. If a node is Red, both children are Black (no two consecutive Reds). 5. Every path from a node to descendant NIL leaves contains an equal count of Black nodes (Black Height). "
                    "B-Trees generalize search trees to multi-way nodes with high branching factor B, minimizing disk block I/O operations in relational database storage engines (PostgreSQL and MySQL InnoDB)."
                )
            },
            {
                "title": "Lecture 7: Dynamic Programming: Optimal Substructure & Memoization",
                "content": (
                    "Dynamic Programming (DP) solves optimization problems by decomposing them into overlapping subproblems and caching intermediate state to prevent combinatorial explosion. "
                    "A problem admits a dynamic programming formulation if and only if it exhibits two fundamental properties: "
                    "1. Optimal Substructure: An optimal solution to the overall problem contains within it optimal solutions to constituent subproblems. "
                    "2. Overlapping Subproblems: A recursive solution repeatedly revisits the exact same subproblems rather than generating new instances. "
                    "Top-down DP utilizes recursive formulation with a memoization hash table or array. Bottom-up DP iteratively populates a state transition table, enabling space optimization via rolling arrays. "
                    "Canonical paradigms include: 0/1 Knapsack (DP[i][w] = max(DP[i-1][w], DP[i-1][w - wt[i]] + val[i])), Longest Common Subsequence (LCS), Matrix Chain Multiplication, and Floyd-Warshall all-pairs shortest paths in O(V^3)."
                )
            },
            {
                "title": "Lecture 9: Advanced Graph Structures: Tarjan's SCC & Network Flow",
                "content": (
                    "Tarjan's Strongly Connected Components (SCC) algorithm identifies maximal subgraphs where every vertex is reachable from every other vertex in linear O(V + E) time using a single Depth-First Search traversal. "
                    "It tracks discovery time dfs_num[u] and lowest reachable ancestor dfs_low[u]. Vertices are pushed onto a stack during traversal; when dfs_low[u] == dfs_num[u], u is the root of an SCC, and all vertices above u on the stack form the component. "
                    "Network Flow: A flow network is a directed graph where each edge has capacity c(u, v) and flow f(u, v) satisfying capacity constraints and conservation of flow. "
                    "The Ford-Fulkerson method augments flow along residual graph paths until no s-t augmenting path exists. The Max-Flow Min-Cut Theorem proves that maximum net flow equals the minimum capacity across all s-t cuts. "
                    "The Edmonds-Karp implementation uses BFS to find shortest augmenting paths, guaranteeing termination in O(V * E^2) time."
                )
            },
            {
                "title": "Handout: Comprehensive DSA Quick-Reference & Invariants Cheatsheet",
                "content": (
                    "Foundational Data Structure Complexity Summary:\n"
                    "- Array / Vector: Access O(1), Search O(N), Insert/Delete O(N) (Amortized append O(1))\n"
                    "- Singly Linked List: Access O(N), Search O(N), Insert/Delete at head O(1), at tail with pointer O(1)\n"
                    "- Hash Table: Average Search/Insert/Delete O(1), Worst-Case O(N) under hash collision clustering\n"
                    "- Binary Heap: Find-Min O(1), Extract-Min O(log N), Insert O(log N), Heapify O(N)\n"
                    "- AVL Tree: Search/Insert/Delete worst-case strictly O(log N), height bounded by 1.44 log_2(N)\n"
                    "- Red-Black Tree: Search/Insert/Delete worst-case O(log N), height bounded by 2 log_2(N + 1)\n"
                    "- Sorting Complexities: QuickSort avg O(N log N) worst O(N^2), MergeSort guaranteed O(N log N) space O(N), HeapSort guaranteed O(N log N) in-place O(1) space, TimSort O(N log N) adaptive."
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
                        },
                        {
                            "id": "q3",
                            "question": "In the Master Theorem recurrence T(n) = 2T(n/2) + O(n), what is the tight asymptotic bound T(n)?",
                            "options": ["O(n)", "O(n log n)", "O(n^2)", "O(log n)"],
                            "correct_answer": "O(n log n)"
                        }
                    ]
                }
            }
        ]
    },
    {
        "code": "CS301",
        "title": "Operating Systems & Kernel Architecture (OS)",
        "description": "Kernel architecture, process lifecycle, thread synchronization primitives, virtual memory management, demand paging, file system inodes, and Linux VFS internals.",
        "syllabus": (
            "Unit 1: Kernel Modes, System Calls, Process Lifecycle & Context Switching\n"
            "Unit 2: Inter-Process Communication (Pipes, Shared Memory, Sockets)\n"
            "Unit 3: Concurrency Primitives (Spinlocks, Mutexes, Semaphores & Deadlock Avoidance)\n"
            "Unit 4: Virtual Memory Management (Paging, Multi-Level Page Tables, TLB, Page Faults)\n"
            "Unit 5: Storage Subsystems (Inodes, Ext4, Linux VFS, Buffer Cache, io_uring)\n"
            "Unit 6: Virtualization & Container Primitives (cgroups v2, Linux Namespaces)"
        ),
        "department": "Computer Science & Engineering",
        "credits": 4,
        "level": "Undergraduate Core",
        "teacher_email": "prof.alan@univ.edu",
        "materials": [
            {
                "title": "Module 1: Process Lifecycle, Context Switching & Kernel IPC",
                "content": (
                    "An operating system process is an executing program instance bundled with private address space, registers, stack pointer, and open file descriptors. "
                    "The kernel tracks process metadata in the Process Control Block (PCB / struct task_struct in Linux). State transitions span: New -> Ready -> Running -> Blocked/Waiting -> Terminated. "
                    "Context Switching: When preempting a process, the kernel executes an assembly trap handler that saves current CPU register state onto the kernel stack, updates the scheduling state, changes the CR3 memory base register to the incoming process's page directory, and restores the incoming registers. "
                    "Inter-Process Communication (IPC): "
                    "1. Unix Pipes: Unidirectional kernel ring buffer with blocking read/write semantics. "
                    "2. POSIX Shared Memory (shm_open / mmap): Fastest IPC mechanism providing direct memory access without kernel copying overhead, requiring synchronization via named semaphores. "
                    "3. Unix Domain Sockets: Bidirectional byte stream or datagram channel residing wholly within kernel space without network protocol stack overhead."
                )
            },
            {
                "title": "Module 2: Virtual Memory, Multi-Level Page Tables & TLB Caching",
                "content": (
                    "Virtual memory isolates application address spaces and provides each process with the illusion of contiguous, dedicated physical memory. "
                    "The Memory Management Unit (MMU) translates virtual addresses to physical addresses using hierarchical page tables. "
                    "On x86-64 hardware, 4-level paging divides a 48-bit canonical virtual address into 9 bits PML4, 9 bits PDP, 9 bits PD, 9 bits PT, and 12 bits page offset (4KB page size). "
                    "Translation Lookaside Buffer (TLB): A hardware associative cache residing inside the CPU core storing recent virtual-to-physical translations. A TLB hit resolves addresses in 1 clock cycle; a TLB miss forces a 4-level memory walk. "
                    "Page Faults: When a virtual address is accessed whose Page Table Entry (PTE) Present bit is 0, the CPU raises an architectural interrupt (Page Fault #PF, Vector 14). "
                    "The kernel verifies the virtual address against process Virtual Memory Areas (VMAs): "
                    "- Minor Page Fault: The physical frame is already allocated or cached in page cache; the kernel maps the PTE without disk I/O. "
                    "- Major Page Fault: The data resides on disk (backing file or swap space); the kernel blocks the process, issues storage DMA reads, updates PTE, and resumes execution."
                )
            },
            {
                "title": "Module 4: Concurrency Primitives: Mutexes, Spinlocks & Peterson's Algorithm",
                "content": (
                    "A Critical Section is a sequence of code accessing shared state where race conditions occur unless mutual exclusion is strictly enforced. "
                    "Hardware provides atomic Read-Modify-Write instructions: Compare-And-Swap (CAS), Test-And-Set (TAS), and Load-Linked/Store-Conditional (LL/SC) enforcing memory bus serialization via MESI cache coherency protocols. "
                    "Spinlocks: Contending threads execute a tight CPU polling loop. Spinlocks minimize latency and are mandatory in non-sleepable kernel contexts (e.g. Interrupt Service Routines), but waste CPU cycles if held for extended durations. "
                    "Mutexes: Contending threads sleep in a wait queue, relinquishing CPU cores to other runnable threads. Modern Linux implements Futex (Fast Userspace Mutex), which performs lock acquisition entirely in userspace via atomic CAS, only escalating to a kernel syscall when contention occurs. "
                    "Peterson's Algorithm: Classic software solution guaranteeing mutual exclusion for two threads using shared flags and a turn variable, satisfying mutual exclusion, progress, and bounded waiting."
                )
            },
            {
                "title": "Module 6: Deadlock Characterization, Prevention & Banker's Algorithm",
                "content": (
                    "A deadlock occurs when a set of concurrent processes are permanently blocked because each process holds a resource while awaiting another held resource. "
                    "Coffman's Four Necessary Conditions for Deadlock: "
                    "1. Mutual Exclusion: At least one resource must be held in a non-shareable mode. "
                    "2. Hold and Wait: A process holds at least one resource while waiting to acquire additional resources. "
                    "3. No Preemption: Resources cannot be forcibly revoked from a process; they must be released voluntarily. "
                    "4. Circular Wait: A closed loop exists where P_0 waits for resource held by P_1, ..., and P_n waits for resource held by P_0. "
                    "Deadlock Avoidance - Dijkstra's Banker's Algorithm: Prior to granting a resource request, the kernel executes a safety check algorithm verifying that an execution sequence exists where all processes can successfully complete and release resources. "
                    "If the resulting state is Safe, the request is granted; if Unsafe, the requesting process is blocked."
                )
            },
            {
                "title": "Module 8: Storage Subsystems, Inode Architecture & Linux Virtual File System (VFS)",
                "content": (
                    "The Linux Virtual File System (VFS) provides a polymorphic abstraction layer decoupling POSIX file syscalls (open, read, write) from underlying storage formats (ext4, xfs, btrfs, nfs). "
                    "Core VFS Data Structures: "
                    "1. Superblock: Describes the entire mounted filesystem geometry, block size, and root inode pointer. "
                    "2. Inode (Index Node): Stores file metadata (owner, permissions, size, timestamps, extent pointers) independent of file name. Inode numbers uniquely identify files on a storage block device. "
                    "3. Dentry (Directory Entry): Caches directory hierarchy in RAM (Dentry Cache / dcache) mapping path strings to inode numbers. "
                    "4. File Object: Represents an open file instance created by sys_open, maintaining the per-process read/write offset and access modes. "
                    "Hard Links point multiple dentries directly to the same underlying inode number; Soft/Symbolic Links store the target filepath string in a separate inode. "
                    "Asynchronous Storage: Modern Linux systems utilize io_uring for kernel-bypass zero-copy asynchronous I/O, replacing legacy synchronous POSIX read/write calls."
                )
            },
            {
                "title": "Handout: Linux Kernel Subsystem Architectural Reference & System Call Guide",
                "content": (
                    "Linux System Call Execution Lifecycle:\n"
                    "1. User application issues system call wrapper function (e.g. read()).\n"
                    "2. CPU executes syscall instruction: switches CPU privilege level from Ring 3 (User) to Ring 0 (Kernel), loading kernel stack pointer.\n"
                    "3. Syscall Dispatcher inspects register RAX for syscall number, indexing sys_call_table.\n"
                    "4. Arguments passed in RDI, RSI, RDX, R10, R8, R9 are copied or verified.\n"
                    "5. Syscall handler completes execution and returns result in RAX.\n"
                    "6. CPU executes sysret instruction, returning execution to userspace Ring 3.\n\n"
                    "Process Creation Architecture: fork() utilizes Copy-On-Write (COW) memory mapping—parent and child share identical read-only physical pages. A physical page allocation occurs only when either process attempts a write operation, raising a Page Fault to clone the single modified frame."
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
        "description": "ARM Cortex-M architecture, bare-metal C programming, memory-mapped I/O, hardware interrupts, timers, ADC, serial protocols (UART/SPI/I2C), and FreeRTOS task scheduling.",
        "syllabus": (
            "Unit 1: ARM Cortex-M Pipeline, Register Model & Memory-Mapped I/O\n"
            "Unit 2: Nested Vectored Interrupt Controller (NVIC) & Timers\n"
            "Unit 3: Serial Communication Protocols (UART, SPI, I2C, CAN Bus)\n"
            "Unit 4: Analog Interfacing & Direct Memory Access (DMA)\n"
            "Unit 5: Real-Time Kernel Scheduling (FreeRTOS Preemption, Queues, Semaphores)\n"
            "Unit 6: Low-Power Modes & Watchdog Timers in Safety-Critical Systems"
        ),
        "department": "Electrical & Computer Engineering",
        "credits": 4,
        "level": "Upper Division",
        "teacher_email": "dr.sarah@univ.edu",
        "materials": [
            {
                "title": "Guide 1: Bare-Metal ARM Interrupts & NVIC Priority Management",
                "content": (
                    "The ARM Cortex-M Nested Vectored Interrupt Controller (NVIC) provides deterministic low-latency hardware interrupt handling. "
                    "When a peripheral signals an Interrupt Request (IRQ), the processor hardware automatically stacks eight core CPU registers: "
                    "R0, R1, R2, R3, R12, Link Register (LR), Program Counter (PC), and Program Status Register (xPSR) onto the current stack pointer before jumping to the vector table handler. "
                    "Interrupt Latency: Typically 12 clock cycles on Cortex-M4. NVIC features Tail-Chaining: if an interrupt is pending when an ISR finishes, the core skips unstacking and immediately vectors to the next ISR in only 6 cycles. "
                    "Interrupt Preemption & Subpriority: NVIC supports configurable priority grouping dividing priorities into Preempt Priority (determines if an incoming IRQ interrupts currently running ISR) and Subpriority (resolves simultaneous pending IRQs). "
                    "Interrupt Service Routines (ISRs) must execute in deterministic, minimal time: heavy computational tasks must be deferred to FreeRTOS worker tasks via Task Notifications or Queues."
                )
            },
            {
                "title": "Guide 3: Serial Communication Protocol Comparison: UART vs SPI vs I2C",
                "content": (
                    "Microcontrollers interface with sensors, actuators, and memory via three primary serial protocols: "
                    "1. UART (Universal Asynchronous Receiver-Transmitter): Asynchronous, point-to-point, full-duplex using two signal lines (TX, RX). Uses start/stop bit framing and optional parity. No shared clock line; transmitters and receivers must agree on predetermined baud rates (e.g. 115200 bps). "
                    "2. SPI (Serial Peripheral Interface): Synchronous, master-slave, full-duplex using four signal lines: MOSI (Master Out Slave In), MISO (Master In Slave Out), SCK (Serial Clock), and CS/SS (Chip Select). Supports speeds exceeding 50 MHz. Uses CPOL (Clock Polarity) and CPHA (Clock Phase) modes 0-3 to dictate sampling edges. "
                    "3. I2C (Inter-Integrated Circuit): Synchronous, multi-master, half-duplex bus using only two bidirectional open-drain lines (SDA for data, SCL for clock) pulled high by external pull-up resistors (typically 4.7k ohm). Devices are addressed using 7-bit or 10-bit identifiers. Supports Standard (100 kbps), Fast (400 kbps), and Fast+ (1 Mbps) modes with built-in ACK/NACK signaling."
                )
            },
            {
                "title": "Guide 5: FreeRTOS Real-Time Kernel Scheduling & Task Synchronization",
                "content": (
                    "FreeRTOS is a deterministic real-time operating system kernel designed for resource-constrained microcontrollers. "
                    "Task States: Running (currently executing on CPU), Ready (runnable, awaiting CPU scheduling), Blocked (awaiting temporal delay or synchronization event), and Suspended. "
                    "Preemptive Scheduling: The scheduler always grants the CPU to the highest-priority Ready task. Tasks of equal priority share the CPU via Round-Robin time slicing driven by the SysTick timer interrupt. "
                    "Inter-Task Synchronization Primitives: "
                    "- Binary Semaphores: Used for task synchronization or peripheral event notification. "
                    "- Counting Semaphores: Used to manage pools of shared hardware resources. "
                    "- Mutexes: Include Priority Inheritance Protocol to prevent Priority Inversion (where a medium-priority task delays a high-priority task waiting on a low-priority lock). "
                    "- Queues: Thread-safe FIFO data structures with deep-copy semantics, allowing safe inter-task data passing without shared variable race conditions."
                )
            },
            {
                "title": "Guide 7: Direct Memory Access (DMA) & ADC Sensor Pipelines",
                "content": (
                    "Direct Memory Access (DMA) transfers data directly between peripherals (ADC, SPI, UART) and SRAM without involving CPU core instructions, eliminating CPU overhead during high-bandwidth streaming. "
                    "DMA Controller Architecture: Configured with source address, destination address, transfer length, and increment modes. "
                    "Circular Buffer Mode: The DMA controller automatically reloads its counter upon completion, continuously streaming incoming peripheral bytes into a ring buffer in memory. "
                    "Interrupts: Generates Half-Transfer Complete (HT) and Transfer Complete (TC) interrupts, enabling ping-pong double buffering where the CPU processes the first half of the buffer while DMA fills the second half without data overrun. "
                    "Successive Approximation Register (SAR) ADC: Samples analog voltages via sample-and-hold capacitors and binary search comparator logic, governed by Nyquist-Shannon Sampling Theorem (sampling frequency f_s >= 2 * f_max)."
                )
            },
            {
                "title": "Handout: Embedded C Hardware Interface & Peripheral Register Guide",
                "content": (
                    "Hardware Register Programming in Embedded C:\n"
                    "- The 'volatile' keyword: Informs the compiler optimizer that a variable's value can change outside program flow (e.g., peripheral status flags, ISR counters), preventing incorrect register caching in CPU registers.\n"
                    "- Memory-Mapped I/O Macros:\n"
                    "  #define GPIOA_BASE (0x40020000UL)\n"
                    "  #define GPIOA_ODR  (*(volatile uint32_t *)(GPIOA_BASE + 0x14))\n"
                    "- Bitwise manipulation rules:\n"
                    "  Set bit 5:   GPIOA_ODR |= (1UL << 5);\n"
                    "  Clear bit 5: GPIOA_ODR &= ~(1UL << 5);\n"
                    "  Toggle bit:  GPIOA_ODR ^= (1UL << 5);\n"
                    "- Watchdog Timer (WDT): Independent hardware counter that resets the microcontroller if firmware freezes or fails to refresh (kick/feed) the watchdog counter within a configured time window."
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
        "description": "Comprehensive grounding in Japanese orthography (Hiragana, Katakana, Kanji), core grammar, verb inflections, polite honorific speech (Keigo), and communicative cultural context.",
        "syllabus": (
            "Unit 1: Phonetics, Syllabaries (Hiragana & Katakana) & SOV Grammar Mechanics\n"
            "Unit 2: Core Particles (Wa, Ga, O, Ni, De, He, To, Mo) & Copula 'Desu'\n"
            "Unit 3: Verb Conjugations (Godan, Ichidan, Irregular) & The Fundamental Te-Form\n"
            "Unit 4: Adjective Inflections, Comparisons & Temporal Subordinate Clauses\n"
            "Unit 5: Honorific Language (Keigo: Teineigo, Sonkeigo, Kenjougo)\n"
            "Unit 6: Business Etiquette, Bowing Culture & Meishi Exchange Protocols"
        ),
        "department": "Modern Languages & International Studies",
        "credits": 3,
        "level": "Introductory Humanities",
        "teacher_email": "dr.sarah@univ.edu",
        "materials": [
            {
                "title": "Unit 1: The Japanese Writing System & Particle Mechanics",
                "content": (
                    "The Japanese language employs three writing scripts concurrently: "
                    "1. Hiragana (46 basic phonetic characters): Used for native Japanese words, verb and adjective inflections (okurigana), and grammatical particles. "
                    "2. Katakana (46 corresponding phonetic characters): Used primarily for foreign loanwords (gairaigo), scientific terms, onomatopoeia, and visual emphasis. "
                    "3. Kanji (logographic characters of Chinese origin): Represent conceptual roots of nouns, verbs, and adjectives. "
                    "Sentence Structure: Japanese follows Subject-Object-Verb (SOV) order. Grammatical relationships are demarcated by postpositional particles: "
                    "- は (wa): Discourse topic marker, setting the contextual frame ('As for X...'). "
                    "- が (ga): Grammatical subject marker, identifies specific agents and marks subjects in subordinate clauses. "
                    "- を (o/wo): Direct object marker for transitive action verbs (e.g., 本を読む - read a book). "
                    "- に (ni): Marks specific points in time, destination, indirect objects, and locations of static existence (with いる/ある). "
                    "- で (de): Marks locations where dynamic actions occur, or the instrument/means of an action (e.g., バスで行く - go by bus)."
                )
            },
            {
                "title": "Unit 2: Essential Verb Conjugations & The Crucial Te-Form",
                "content": (
                    "Japanese verbs are classified into three distinct inflectional categories: "
                    "1. Ichidan (Group 2 / Ru-verbs): Stem ends in -iru or -eru. Conjugation removes -ru and appends suffixes (e.g., 食べる taberu -> 食べます tabemasu, 食べて tabete). "
                    "2. Godan (Group 1 / U-verbs): Stem ends in nine consonant endings (u, ku, gu, su, tsu, nu, bu, mu, ru). Conjugation alters the final vowel across the five Japanese vowel rows (a, i, u, e, o). "
                    "3. Irregular (Group 3): Exactly two verbs: する (suru -> します shimasu, して shite) and 来る (kuru -> 来ます kimasu, 来て kite). "
                    "The Te-Form (て形) Conjugation Rules for Godan Verbs: "
                    "- Verbs ending in う (u), つ (tsu), る (ru) -> って (tte) [e.g., 待つ matsu -> 待って matte] "
                    "- Verbs ending in む (mu), ぶ (bu), ぬ (nu) -> んで (nde) [e.g., 飲む nomu -> 飲んで nonde] "
                    "- Verbs ending in く (ku) -> いて (ite) [exception: 行く iku -> 行って itte] "
                    "- Verbs ending in ぐ (gu) -> いで (ide) [e.g., 泳ぐ oyogu -> 泳いで oyoide] "
                    "- Verbs ending in す (su) -> して (shite) [e.g., 話す hanasu -> 話して hanashite] "
                    "Key Functions of the Te-form: Sequential actions (do X and then Y), polite requests (-てください), continuous present progressive aspect (-ています), and requesting permission (-てもいいですか)."
                )
            },
            {
                "title": "Unit 3: Honorific Language (Keigo) & Cultural Etiquette",
                "content": (
                    "Keigo (敬語) is the Japanese system of polite, respectful, and humble speech reflecting social hierarchy, in-group vs out-group dynamics (Uchi vs Soto), and situational formality. "
                    "Keigo is subdivided into three principal linguistic registers: "
                    "1. 丁寧語 (Teineigo - Polite Speech): General polite standard characterized by the copula 'desu' and the verbal suffix '-masu', used in everyday interactions with acquaintances. "
                    "2. 尊敬語 (Sonkeigo - Respectful Speech): Elevates the actions, possessions, and state of the interlocutor or a higher-status counterpart. Canonical transformations: "
                    "   - する (suru) -> なさる (nasaru) "
                    "   - 言う (iu) -> おっしゃる (ossharu) "
                    "   - 行く/来る/いる -> いらっしゃる (irassharu) "
                    "   - 食べる/飲む -> 召し上がる (meshiagaru) "
                    "   - Prefixing nouns with honorific お- (O-) or ご- (Go-). "
                    "3. 謙譲語 (Kenjougo - Humble Speech): Lowers the speaker's own actions and those of their in-group (family, company colleagues) to show deference: "
                    "   - する -> いたす (itasu) "
                    "   - 言う -> 申す (mousu) "
                    "   - 行く/来る -> 参る (mairu) "
                    "   - 見る -> 拝見する (haiken suru)."
                )
            },
            {
                "title": "Unit 4: Adjective Inflections, Comparisons & Temporal Clauses",
                "content": (
                    "Japanese features two distinct adjective classes with separate inflectional morphologies: "
                    "1. い-Adjectives (i-keiyoushi): True adjectives ending in -i. Conjugate directly: "
                    "   - Present Aff: 高い (takai - expensive) "
                    "   - Present Neg: 高くない (takakunai) "
                    "   - Past Aff: 高かった (takakatta) "
                    "   - Past Neg: 高くなかった (takakunakatta) "
                    "   - Adverbial form: replace -i with -ku (e.g. 早く走る - run quickly). "
                    "2. な-Adjectives (na-keiyoushi): Adjectival nouns requiring 'na' when modifying nouns directly (e.g. 静かな部屋 - quiet room). Inflect via the copula 'desu/da' (静かでした, 静かではありません). "
                    "Comparative Constructions: "
                    "- Formula: A は B より [Adjective] です (A is more [Adjective] than B). "
                    "- Formula: A と B と どちらが [Adjective] ですか (Between A and B, which is more [Adjective]?). "
                    "Temporal Clauses: "
                    "- [Verb Dictionary Form] 前に (mae ni): Before doing [Verb]. "
                    "- [Verb Ta-form (Past)] 後で (ato de): After doing [Verb]. "
                    "- [Verb Stem] ながら (nagara): Simultaneous action (doing X while doing Y)."
                )
            },
            {
                "title": "Handout: JLPT N5-N4 High-Yield Grammar Handbook & Business Etiquette",
                "content": (
                    "Essential Conversational & Business Etiquette Reference:\n"
                    "1. Greetings & Everyday Expressions:\n"
                    "   - 初めまして、よろしくお願いします (Hajimemashite, yoroshiku onegaishimasu - Nice to meet you, please treat me favorably).\n"
                    "   - お疲れ様です (Otsukaresama desu - Thank you for your hard work, standard workplace greeting).\n"
                    "   - お世話になっております (Osewa ni natte orimasu - Thank you for your continued business/support).\n"
                    "2. Business Card Exchange (名刺交換 - Meishi Koukan):\n"
                    "   - Always present business cards with both hands, card facing the recipient so they can read it immediately.\n"
                    "   - State your affiliation and name: [Company] の [Name] と申します。\n"
                    "   - Receive the counterpart's card with both hands and say 頂戴いたします (Choudai itashimasu).\n"
                    "   - Never write on the received card or put it directly into a pocket; place it carefully atop the cardholder on the meeting table.\n"
                    "3. Bowing Protocol (お辞儀 - Ojigi):\n"
                    "   - 会釈 (Eshaku - 15 degree bow): Casual greeting to colleagues.\n"
                    "   - 敬礼 (Keirei - 30 degree bow): Standard respectful business bow for clients and supervisors.\n"
                    "   - 最敬礼 (Saikeirei - 45 degree bow): Deep bow expressing profound gratitude or formal apology."
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
                        },
                        {
                            "id": "q3",
                            "question": "Which keigo speech category elevates the actions of the customer or counterpart?",
                            "options": ["Teineigo (丁寧語)", "Sonkeigo (尊敬語)", "Kenjougo (謙譲語)", "Futsuugo (普通語)"],
                            "correct_answer": "Sonkeigo (尊敬語)"
                        }
                    ]
                }
            }
        ]
    },
    {
        "code": "CS401",
        "title": "Machine Learning & Neural Foundations (ML)",
        "description": "Statistical learning theory, convex optimization, regularization (L1/L2), kernel methods, ensemble learning, neural architectures, backpropagation calculus, and deep attention models.",
        "syllabus": (
            "Unit 1: Supervised Learning Foundations, Loss Functions & Convex Optimization\n"
            "Unit 2: Regularization Techniques (Ridge L2, Lasso L1, ElasticNet) & Bias-Variance Tradeoff\n"
            "Unit 3: Support Vector Machines (SVMs), Karush-Kuhn-Tucker (KKT) & The Kernel Trick\n"
            "Unit 4: Deep Neural Networks, Backpropagation Calculus & Activation Dynamics\n"
            "Unit 5: Convolutional Networks & Deep Residual Learning (ResNet)\n"
            "Unit 6: Transformer Architectures & Scaled Dot-Product Self-Attention Mechanisms"
        ),
        "department": "Computer Science & Artificial Intelligence",
        "credits": 4,
        "level": "Upper Division / Graduate",
        "teacher_email": "prof.alan@univ.edu",
        "materials": [
            {
                "title": "Lecture 1: Linear Models, Convex Optimization & Regularization (L1 vs L2)",
                "content": (
                    "Linear regression models target variable y as a linear combination of input features X and weight parameters theta: y_hat = X * theta. "
                    "The Ordinary Least Squares (OLS) objective minimizes Mean Squared Error (MSE): J(theta) = (1/2N) * ||X*theta - y||_2^2. "
                    "The closed-form analytical solution is given by the Normal Equation: theta = (X^T * X)^(-1) * X^T * y, requiring O(d^3) computation. "
                    "Collinearity & Overfitting: When feature dimensions are correlated, X^T * X becomes singular or ill-conditioned. Regularization restores numerical stability: "
                    "1. Ridge Regression (L2 Regularization): Adds penalty term lambda * ||theta||_2^2. Equivalent to a zero-mean Gaussian prior on weights. Shrinks weights proportionally toward zero, stabilizing variance under multicollinearity. "
                    "2. Lasso Regression (L1 Regularization): Adds penalty term lambda * ||theta||_1. Equivalent to a Laplace prior. Because the L1 constraint boundary forms a sharp diamond with corners on coordinate axes, gradients drive non-informative feature weights to exact zero, performing automatic feature selection and inducing sparse representations. "
                    "3. ElasticNet: Convex combination of L1 and L2 penalties, overcoming Lasso's limitation where it selects at most N features when d > N."
                )
            },
            {
                "title": "Lecture 2: Gradient Descent Optimization & Convex Loss Surfaces",
                "content": (
                    "Gradient descent is an iterative first-order optimization algorithm minimizing differentiable loss functions J(theta). "
                    "Parameters update in the negative gradient direction: theta := theta - alpha * grad(J(theta)), where alpha is the learning rate. "
                    "Variants: "
                    "- Batch Gradient Descent: Evaluates the exact gradient over all N training samples, providing stable convergence but becoming prohibitively expensive on massive datasets. "
                    "- Stochastic Gradient Descent (SGD): Approximates the true gradient using a single random sample or mini-batch, adding stochastic gradient noise that helps escape shallow local minima. "
                    "Advanced Adaptive Optimizers: "
                    "- Momentum (Polyak Heavy Ball): Accumulates velocity v := beta * v + alpha * grad(J(theta)) to accelerate along persistent downhill directions and dampen orthogonal oscillations. "
                    "- RMSProp: Normalizes parameter updates by an exponential moving average of squared gradients, resolving ill-conditioned ravines. "
                    "- Adam (Adaptive Moment Estimation): Integrates first-moment estimation (mean of gradients) and second-moment estimation (uncentered variance of gradients) with analytical bias-correction factors: "
                    "m_hat = m_t / (1 - beta_1^t), v_hat = v_t / (1 - beta_2^t), updating theta := theta - alpha * m_hat / (sqrt(v_hat) + epsilon)."
                )
            },
            {
                "title": "Lecture 3: Support Vector Machines, The Dual Formulation & Kernel Trick",
                "content": (
                    "Support Vector Machines (SVMs) find the optimal maximum-margin separating hyperplane w^T * x + b = 0 between two classes. "
                    "The geometric margin equals 2 / ||w||_2. Maximizing the margin corresponds to minimizing (1/2) * ||w||_2^2 subject to classification constraints y_i * (w^T * x_i + b) >= 1. "
                    "Soft-Margin SVM: Accommodates non-separable noise using slack variables xi_i and regularization parameter C balancing margin width against misclassification penalties. "
                    "Lagrange Dual Formulation: Using Karush-Kuhn-Tucker (KKT) conditions, the optimization objective transforms into a quadratic programming dual problem depending purely on inner products between input pairs: (x_i^T * x_j). "
                    "The Kernel Trick: Projects input data into higher-dimensional Hilbert space Phi(x) without explicitly computing coordinates, replacing inner products with a kernel function K(x_i, x_j) = <Phi(x_i), Phi(x_j)>: "
                    "- Linear Kernel: K(x, z) = x^T * z "
                    "- Polynomial Kernel: K(x, z) = (x^T * z + c)^d "
                    "- Radial Basis Function (RBF / Gaussian) Kernel: K(x, z) = exp(-gamma * ||x - z||_2^2), which maps inputs into an infinite-dimensional feature space."
                )
            },
            {
                "title": "Lecture 5: Neural Network Backpropagation & Computational Graphs",
                "content": (
                    "Backpropagation computes the partial derivative of the scalar loss function with respect to every weight parameter in a deep neural network via the Multivariable Chain Rule. "
                    "Forward Pass: Input activations a^(0) = x propagate forward through successive layers l = 1, ..., L: "
                    "z^(l) = W^(l) * a^(l-1) + b^(l), a^(l) = sigma(z^(l)), where sigma is a non-linear activation function. "
                    "Backward Pass: Computes error delta^(L) = grad_a J odot sigma'(z^(L)). For hidden layers, errors propagate backward: "
                    "delta^(l) = ((W^(l+1))^T * delta^(l+1)) odot sigma'(z^(l)). "
                    "Parameter gradients are evaluated as: dJ/dW^(l) = delta^(l) * (a^(l-1))^T, and dJ/db^(l) = delta^(l). "
                    "Activation Functions & Gradients: "
                    "- Sigmoid: sigma(z) = 1 / (1 + exp(-z)). Maximum derivative is 0.25, causing vanishing gradients in deep networks. "
                    "- Rectified Linear Unit (ReLU): f(z) = max(0, z). Constant gradient of 1 for z > 0, mitigating vanishing gradients but vulnerable to 'Dying ReLU' if units become permanently inactive. "
                    "- GELU (Gaussian Error Linear Unit): f(z) = z * Phi(z), standard in modern Transformer architectures."
                )
            },
            {
                "title": "Lecture 7: Deep Learning Architectures: Convolutional & Transformer Networks",
                "content": (
                    "Convolutional Neural Networks (CNNs) process grid-structured data (images, spectrograms) leveraging local receptive fields, parameter sharing, and translation equivariance. "
                    "Deep Residual Networks (ResNet) introduce identity shortcut skip connections: y = F(x, {W_i}) + x. "
                    "Skip connections allow error gradients to flow directly backward through the residual addition operator without vanishing, enabling training of networks exceeding 100 layers. "
                    "The Transformer Architecture: Dispenses with recurrent sequential steps, relying entirely on the Self-Attention mechanism to model long-range dependencies in parallel. "
                    "Scaled Dot-Product Attention: Projects input embeddings into Queries (Q), Keys (K), and Values (V) via learned matrices W_Q, W_K, W_V: "
                    "Attention(Q, K, V) = Softmax((Q * K^T) / sqrt(d_k)) * V. "
                    "The scaling factor 1 / sqrt(d_k) prevents dot products from growing excessively large in high dimensions, preventing softmax gradients from saturating. "
                    "Multi-Head Attention projects queries, keys, and values across h distinct representation subspaces, enabling the model to simultaneously attend to syntax, semantics, and context."
                )
            },
            {
                "title": "Handout: Machine Learning Mathematical Invariants & Optimization Reference",
                "content": (
                    "Foundational Machine Learning Mathematical Invariants:\n"
                    "1. Loss Functions:\n"
                    "   - Mean Squared Error (MSE): L(y, y_hat) = (1/2) * (y - y_hat)^2\n"
                    "   - Binary Cross-Entropy (BCE): L(y, p) = -[y * log(p) + (1 - y) * log(1 - p)]\n"
                    "   - Categorical Cross-Entropy (CCE): L(y, p) = -sum_k y_k * log(p_k)\n"
                    "2. Bias-Variance Decomposition:\n"
                    "   - Expected Test Error = Bias^2[f_hat] + Var[f_hat] + sigma_irreducible^2\n"
                    "   - High Bias = Underfitting (model too simplistic; add features, decrease regularization)\n"
                    "   - High Variance = Overfitting (model captures noise; add data, augment data, increase L1/L2 penalty, apply Dropout)\n"
                    "3. Model Evaluation Metrics:\n"
                    "   - Precision = TP / (TP + FP)\n"
                    "   - Recall / Sensitivity = TP / (TP + FN)\n"
                    "   - F1-Score = 2 * (Precision * Recall) / (Precision + Recall)\n"
                    "   - ROC-AUC: Area under True Positive Rate vs False Positive Rate curve across varying decision thresholds."
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
