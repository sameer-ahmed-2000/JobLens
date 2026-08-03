"""add extraction_method to resume_files

Revision ID: 0008_resume_extraction_method
Revises: 0007_resume_files_and_versioning
Create Date: 2026-08-03 11:00:00.000000

Records which extraction path was used to read a PDF:
  - "text_layer" — fast path, embedded text found by pdfplumber/pypdf/pymupdf
  - "ocr"         — Tesseract OCR fallback (scanned/image-only PDFs)
  - "vision_ocr"  — Gemini Vision API fallback (dev env without Tesseract)

Nullable so existing rows are unaffected without a backfill.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0008_resume_extraction_method'
down_revision: Union[str, None] = '0007_resume_files_and_versioning'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('resume_files', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('extraction_method', sa.String(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table('resume_files', schema=None) as batch_op:
        batch_op.drop_column('extraction_method')
