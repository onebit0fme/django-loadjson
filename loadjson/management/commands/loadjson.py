from django.core.management.base import BaseCommand
from ...loaders import TransferData


class Command(BaseCommand):
    help = "Transfer data from json"

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('json_path',
                            type=str,
                            help="Provide data file path")

    def handle(self, *args, **options):
        data_path = options['json_path']
        td = TransferData(data_name=data_path)
        td.import_data(write_to_std_out=True)

        # REPORT
        if td.report.exceptions:
            self.stdout.write("EXCEPTIONS")
        for exc_type, exc_list in iter(td.report.exceptions.items()):
            self.stdout.write(exc_type + "<" * 30)
            if len(exc_list) > 10:
                self.stdout.write("    - {} ERRORS".format(len(exc_list)))
            else:
                for message in exc_list:
                    self.stdout.write("    - {}".format(message))
            self.stdout.write("^" * 40)
        self.stdout.write(" Done!")
        self.stdout.write("CREATED - {}".format(td.report.created))
        self.stdout.write("UPDATED - {}".format(td.report.updated))
