

class BaseAdaptor(object):
    """
    `models` - a list of models in a format "<app_label>.<model_name>" that the adaptor is applied to.

    Note:
    - adaptors run in order of it's definition
    - adaptors data is modified by a previous adaptor
    - you should not rely on data being changed by the previous adaptor, since this behaviour is likely to change
    """
    models = None

    def __init__(self, model, app_model, manifest):
        self.model = model
        self.app_model = app_model
        self.manifest = manifest

    def adapt(self, data):
        """
        Method provides a base hook to provide additional data, set defaults,
        or modify the data before saving. Heavy data modification is discouraged here,
        best practice is to define  custom parsers.

        Usage: what returned gets saved
        """
        return data

    def adapt_post_save(self, obj, data, m2m_data):
        """
        In some cases (like saving many-to-many relations) data might require
        some additional tweaks. That is done here.
        Note: Many-to-Many objects are attached by default, however case if many-to-many relationship
        is done through a custom model, this method provides a hook to process such customization.
        """
        pass
