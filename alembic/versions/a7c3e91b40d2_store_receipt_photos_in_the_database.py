"""store receipt photo bytes in session_photos

Photos were kept in a process-local dict (``app.state.photo_storage``) with no eviction.
Three consequences, all of them real:

* a restart orphaned every in-flight session — the session_photos rows survived but the
  bytes did not, so OCR answered "No photos available" with no way to recover;
* the API could never run more than one worker, since only the worker that accepted the
  upload could see the bytes;
* nothing ever removed them, so the dict grew for the life of the process.

Holding them on the row fixes all three, and cleanup comes free: session_photos.session_id
already cascades (migration f1a2b3c4d5e6), so photos die with their session. The column is
also nulled right after a successful OCR, which is where essentially all of the volume
goes — a receipt's bytes are needed for minutes, between upload and recognition.

Nullable and deferred (see core/models/session.py): Session.photos is lazy="selectin", so a
non-deferred column would attach megabytes of JPEG to every session read.

Revision ID: a7c3e91b40d2
Revises: f1a2b3c4d5e6
Create Date: 2026-08-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c3e91b40d2"
down_revision: Union[str, Sequence[str], None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("session_photos", sa.Column("data", sa.LargeBinary(), nullable=True))


def downgrade() -> None:
    op.drop_column("session_photos", "data")
