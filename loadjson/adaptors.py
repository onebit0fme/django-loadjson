

class BaseAdaptor(object):
    """
    `models` - a list of models in a format "<app_label>.<model_name>" that the adaptor is applied to.

    Note:
    - adaptors run in order of it's definition
    - adaptors data is modified by a previous adaptor
    - you should not rely on data being changed by the previous adaptor, since this behaviour is likely to change
    """
    models = None

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

class DataDefaults(object):

    def __init__(self, *args, **kwargs):
        self.include_updated = kwargs.get('include_updated', True)
        self.from_obj = kwargs.get('from_obj')
        self.default_methods = args
        self.post_save_methods = kwargs.get('post_save_methods')

    def __call__(self, data, transfer_instance=None):
        for d in self.default_methods:
            m = getattr(self, 'default_'+d, None)
            if m is not None:
                data = m(data)
        return data

    def default_created_by(self, data):
        if 'created_by' not in data:
            data['created_by'] = getattr(data.get(self.from_obj), 'created_by')
        if self.include_updated and 'updated_by' not in data:
            updated_by = getattr(data.get(self.from_obj), 'updated_by') or getattr(data.get(self.from_obj), 'created_by')
            data['updated_by'] = updated_by
        return data

    def default_answer_status(self, data):
        is_correct = data.get('is_correct', False)
        is_correct = 100 if is_correct else -100
        data['is_correct'] = is_correct
        data['is_accepted'] = True
        return data

    def default_class_role(self, data):
        role_class = data.pop('class')
        is_manager = data.pop('manager')
        if role_class is None:
            return data
        if is_manager:
            role = ClassRole.objects.get_or_create(name="Moderators",
                                                   role_class=role_class)[0]
        else:
            role = ClassRole.objects.get_or_create(name="Members",
                                                   role_class=role_class,
                                                   default=True)[0]
        data['role'] = role
        data['invitation'] = False
        return data

    def default_legacy(self, data):
        data['legacy'] = True
        return data

    def default_content(self, data):
        url = data.pop('url', '')
        source = data.pop('source', '')
        text = data.get('content', '')
        if url or source:
            annotation = u"\n\n{source} {url}".format(source=source,
                                                     url="({})".format(url))
        else:
            annotation = ''
        content = u"{content}{annotation}".format(content=text,
                                                  annotation=annotation)
        data['content'] = content
        return data

    def ps_say_vote(self, obj, data, m2m_data):
        votes = m2m_data.get('votes')
        if votes is None:
            return
        for vote in votes:
            SayVote.objects.get_or_create(say=obj,
                                          user=vote)

    def post_save(self, obj, data, m2m_data):
        for ps in self.post_save_methods:
            m = getattr(self, "ps_"+ps)
            if m is not None:
                m(obj, data, m2m_data)
