import unittest
from io import BytesIO
from reportlab.pdfgen import canvas

from bot.services.quiz_service import (
    fingerprint, grant_premium, revoke_premium, is_premium,
    create_quiz, add_question, cancel_quiz_creation,
)
from bot.services.pdf_service import chunk_text, extract_pdf_text
from bot.database.db import init_db


class ServiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_fingerprint_normalizes_whitespace_and_case(self):
        self.assertEqual(
            fingerprint(" Hello  world ", ["A", "B", "C", "D"]),
            fingerprint("hello world", ["A", "B", "C", "D"]),
        )

    def test_chunk_text_overlap_and_validation(self):
        text = "0123456789" * 3
        chunks = chunk_text(text, size=12, overlap=3)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0][-3:], chunks[1][:3])
        with self.assertRaises(ValueError):
            chunk_text(text, size=5, overlap=5)

    def test_chunk_text_empty(self):
        self.assertEqual(chunk_text(""), [])

    def test_extract_rejects_invalid_pdf(self):
        with self.assertRaises(ValueError):
            extract_pdf_text(b"not a pdf", ocr=False)

    def test_extract_selectable_pdf_text_and_page_number(self):
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)
        pdf.drawString(72, 720, "PSCGram PDF extraction test")
        pdf.showPage()
        pdf.save()
        extracted = extract_pdf_text(buffer.getvalue(), ocr=False)
        self.assertIn("[PDF page 1]", extracted)
        self.assertIn("PSCGram PDF extraction test", extracted)

    def test_cancel_empty_quiz_deletes_it(self):
        quiz_id = create_quiz("Cancellation test empty")
        cancel_quiz_creation(quiz_id)
        from bot.database.db import SessionLocal
        from bot.database.models import Quiz
        with SessionLocal() as db:
            self.assertIsNone(db.get(Quiz, quiz_id))

    def test_cancel_quiz_with_saved_questions_deactivates_it(self):
        quiz_id = create_quiz("Cancellation test with question")
        saved = add_question(
            "Unique cancellation test question?",
            ["One", "Two", "Three", "Four"],
            0,
            quiz_id=quiz_id,
            subject="Test",
            topic="Cancellation",
        )
        self.assertTrue(saved)
        cancel_quiz_creation(quiz_id)
        from bot.database.db import SessionLocal
        from bot.database.models import Quiz, Question
        with SessionLocal() as db:
            quiz = db.get(Quiz, quiz_id)
            self.assertFalse(quiz.is_active)
            self.assertEqual(
                db.query(Question).filter_by(quiz_id=quiz_id).count(), 1
            )

    def test_premium_duration_must_be_positive(self):
        with self.assertRaises(ValueError):
            grant_premium(987654321013, 0)

    def test_premium_grant_and_revoke_persist(self):
        user_id = 987654321012
        grant_premium(user_id, 7)
        self.assertTrue(is_premium(user_id))
        revoke_premium(user_id)
        self.assertFalse(is_premium(user_id))


if __name__ == "__main__":
    unittest.main()
