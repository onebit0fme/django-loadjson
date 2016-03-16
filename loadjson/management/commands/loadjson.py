from django.core.management.base import BaseCommand
from ...adaptors import DataDefaults
from ...loaders import TransferData

DEFAULTS = {
    "question.Question": DataDefaults('created_by', from_obj='stack'),
    "question.QuestionAnswer": DataDefaults('created_by', 'answer_status',
                                            from_obj='question'),
    "class.RoleUser": DataDefaults('class_role'),
    "say.Say": DataDefaults('content', post_save_methods=['say_vote']),
    "accounts.User": DataDefaults('legacy')
}

M2M = {
    "class.Class": ["stacks"],
    "say.Say": ["votes"]
}


class Command(BaseCommand):
    help = "Transfer data from json"

    def add_arguments(self, parser):
        # Positional arguments
        parser.add_argument('json_path',
                            type=str,
                            help="Provide data file path")

    def handle(self, *args, **options):
        data_path = options['json_path']
        td = TransferData(data_path)
        td.import_data()

        self.stdout.write("Done!")
