from src.rag.vector_store import LMSVectorStore
from src.db.connection import execute_sql_query
import logging

logger = logging.getLogger(__name__)


class KnowledgeBuilder:
    def __init__(self):
        self.vector_store = LMSVectorStore()

    def build_data_patterns_knowledge(self):
        """Extract and vectorize data patterns from the database"""
        knowledge_docs = []

        # Try to extract various data patterns
        patterns = [
            self._extract_course_patterns,
            self._extract_user_patterns,
            self._extract_assignment_patterns,
            self._extract_enrollment_patterns,
        ]

        for pattern_func in patterns:
            try:
                docs = pattern_func()
                knowledge_docs.extend(docs)
            except Exception as e:
                logger.warning(f"Could not extract {pattern_func.__name__}: {e}")

        # Add to vector store
        if knowledge_docs:
            self.vector_store.add_documents(knowledge_docs)
            logger.info(f"Added {len(knowledge_docs)} data pattern documents to knowledge base")

        return knowledge_docs

    def _extract_course_patterns(self):
        """Extract course-related data patterns"""
        try:
            course_stats = execute_sql_query(
                """
                SELECT name, created_at, is_public
                FROM canvas_course
                LIMIT 20
            """
            )

            docs = []
            for course in course_stats:
                doc = f"Course '{course.get('name', 'Unknown')}' created on {course.get('created_at', 'unknown date')}. Public: {course.get('is_public', False)}"
                docs.append(doc)
            return docs
        except Exception as e:
            logger.warning(f"Could not extract course patterns: {e}")
            return []

    def _extract_user_patterns(self):
        """Extract user-related data patterns"""
        try:
            user_stats = execute_sql_query(
                """
                SELECT role, COUNT(*) as count
                FROM canvas_user
                GROUP BY role
            """
            )

            docs = []
            for user in user_stats:
                doc = f"User role distribution: {user['count']} users with role '{user['role']}'"
                docs.append(doc)
            return docs
        except Exception as e:
            logger.warning(f"Could not extract user patterns: {e}")
            return []

    def _extract_assignment_patterns(self):
        """Extract assignment-related data patterns"""
        try:
            assignment_stats = execute_sql_query(
                """
                SELECT title, points_possible, submission_types
                FROM canvas_assignment
                LIMIT 20
            """
            )

            docs = []
            for assignment in assignment_stats:
                doc = f"Assignment '{assignment.get('title', 'Unknown')}' worth {assignment.get('points_possible', 0)} points, type: {assignment.get('submission_types', 'unknown')}"
                docs.append(doc)
            return docs
        except Exception as e:
            logger.warning(f"Could not extract assignment patterns: {e}")
            return []

    def _extract_enrollment_patterns(self):
        """Extract enrollment-related data patterns"""
        try:
            enrollment_stats = execute_sql_query(
                """
                SELECT type, COUNT(*) as count
                FROM enrollment
                GROUP BY type
            """
            )

            docs = []
            for enrollment in enrollment_stats:
                doc = f"Enrollment type '{enrollment['type']}': {enrollment['count']} enrollments"
                docs.append(doc)
            return docs
        except Exception as e:
            logger.warning(f"Could not extract enrollment patterns: {e}")
            return []

    def add_business_rules(self):
        """Add LMS-specific business rules"""
        business_rules = [
            "Students can only see their own grades and submissions in a course",
            "Teachers can view all student data for courses they teach",
            "Users can have different roles in different courses (Student, Teacher, TA)",
            "Assignments have due dates and can accept various submission types",
            "Courses contain multiple assignments, discussions, and modules",
            "Grades are stored in the gradebook and linked to assignments and users",
            "Submissions are linked to assignments and users with scores and feedback",
            "Discussions are organized by topics with replies from enrolled users",
            "Enrollments determine user access to course content and activities",
            "Course modules organize content and assignments in a sequence",
        ]

        self.vector_store.add_documents(business_rules)
        logger.info(f"Added {len(business_rules)} business rules to knowledge base")
        return business_rules

    def add_query_examples(self):
        """Add successful query examples"""
        query_examples = [
            "To find all students in a course: SELECT u.name FROM canvas_user u JOIN enrollment e ON u.id = e.user_id WHERE e.course_id = ? AND u.role = 'student'",
            "To get course assignments: SELECT title, points_possible, due_date FROM canvas_assignment WHERE course_id = ? ORDER BY due_date",
            "To calculate average grades: SELECT user_id, AVG(score) as avg_score FROM canvas_gradebook WHERE course_id = ? GROUP BY user_id",
            "To find user submissions: SELECT a.title, s.score, s.submitted_at FROM canvas_submission s JOIN canvas_assignment a ON s.assignment_id = a.id WHERE s.user_id = ?",
            "To count enrollments per course: SELECT c.name, COUNT(e.user_id) as student_count FROM canvas_course c LEFT JOIN enrollment e ON c.id = e.course_id GROUP BY c.id, c.name",
        ]

        self.vector_store.add_documents(query_examples)
        logger.info(f"Added {len(query_examples)} query examples to knowledge base")
        return query_examples
