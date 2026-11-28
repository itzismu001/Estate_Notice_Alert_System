import json

from django.core.management.base import BaseCommand, CommandError

from documents.services.processing_recovery import (
    ProcessingRecoveryError,
    recover_interrupted_processing,
)


class Command(BaseCommand):
    help = (
        "Safely recover an interrupted document processing job."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--document-id",
            type=int,
            required=True,
            help="ID of the document to recover.",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview recovery without changing the database.",
        )

        parser.add_argument(
            "--confirm-worker-stopped",
            action="store_true",
            help="Confirm the original processing worker has stopped.",
        )

    def handle(self, *args, **options):
        document_id = options["document_id"]
        dry_run = options["dry_run"]
        confirmed = options["confirm_worker_stopped"]

        if not dry_run and not confirmed:
            raise CommandError(
                "Use --dry-run to preview recovery or "
                "--confirm-worker-stopped to perform recovery."
            )

        try:
            result = recover_interrupted_processing(
                document_id=document_id,
                dry_run=dry_run,
                confirm_worker_stopped=confirmed,
            )

        except ProcessingRecoveryError as error:
            raise CommandError(str(error)) from error

        self.stdout.write(
            json.dumps(result, indent=4, default=str)
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "DRY RUN: No database changes were made."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "Processing recovery completed successfully."
                )
            )

        self.stdout.write(
            "No new Celery task was submitted."
        )
