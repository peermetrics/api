from django.db import models
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.html import format_html
from dirtyfields import DirtyFieldsMixin

from ..errors import PMError, INVALID_PARAMETERS
from ..logger import log

class BaseModel(DirtyFieldsMixin, models.Model):
    """
    Wrapper over the standard Django model class.

    Attrs:
        cache_keys: combinations of fields used to compose the keys used to cache the object, overwritten in subclasses

    Fields:
        created_at: time when the model was created
        is_active:
    """
    class Meta:
        abstract = True

    cache_keys = ()

    def set_values(self, values):
        """
        Changes the model attributes in bulk.

        :param values: a dict containing the new values
        :return True if the object has been altered, False otherwise
        """
        changed = False
        for key, value in values:
            if value is not None and getattr(self, key) != value:
                self.__setattr__(key, value)
                changed = True
        return changed

    def save(self, *args, **kwargs):
        """
        Wrapper over standard save method that raises our custom exception if there are validation errors.
        Also it saves the object in cache.

        :raises PMError
        """
        if not self.is_dirty(check_relationship=True):
            return

        try:
            self.clean_fields()
        except ValidationError as exc:
            log.warning(exc)
            raise PMError(status=400, app_error=INVALID_PARAMETERS)

        super().save(*args, **kwargs)
        self.save_cache()

    def soft_delete(self):
        self.is_active = False
        self.save()
        self.delete_cache()

    def save_cache(self):
        """
        Saves the current state of the object in cache.
        If the object is inactive then it doesn't do anything.
        """
        if not self.is_active:
            return

        # we cache the object's dict instead of the whole object to avoid recursively caching the object's relations
        d = self.__dict__.copy()
        # remove some unneeded properties from the object
        d.pop('_state', None)
        d.pop('_django_version', None)
        d.pop('_original_state', None)

        for cache_key in self.cache_keys:
            cache.set(self.get_cache_key({key: getattr(self, key) for key in cache_key}), d, timeout=settings.REDIS_KEY_TTL)

    def delete_cache(self):
        """
        Deletes the occurences of this object from the cache.
        """
        for cache_key in self.cache_keys:
            cache.delete(self.get_cache_key({key: getattr(self, key) for key in cache_key}))

    @classmethod
    def get_cache_key(cls, kwargs):
        """
        Builds a cache key using the caching criteria. The output format:

        class_name=key1:value1[...=keyn:valuen]

        :param kwargs: the caching criteria
        :return the cache key
        """
        key = cls.get_type()
        for k in sorted(kwargs.keys()):
            key = ''.join([key, '=', k, ':', str(kwargs[k])])
        return key

    @classmethod
    def get(cls, *args, **kwargs):
        """
        Wrapper over the standard get method.
        Searches the cache for the object using the query criteria and rebuilds the object if it's found. If the object
        is not found in cache then it queries the database (adding the 'is_active' flag) and caches the returned
        object.

        :param args: the anonymous query criteria
        :param kwargs: the named (key word) query criteria
        :return the queried object (from cache or db)
        """
        # if the query criteria is present in the cache_keys class tuple
        try:
            if sorted(kwargs.keys()) in cls.cache_keys:
                cached = cache.get(cls.get_cache_key(kwargs))  # query the cache
                # if the object is present in cache then rebuild the object using the class constructor
                if cached:
                    obj = cls(**cached)
                    obj.prepare()
                    if obj.is_dirty():
                        obj.save_cache()
                    return obj
        except Exception as e:
            pass

        kwargs['is_active'] = True
        obj = cls.objects.get(*args, **kwargs)  # query the database
        obj.prepare()
        obj.save_cache()
        return obj

    @classmethod
    def get_or_create(cls, *args, **kwargs):
        """
        Wrapper over the standard get_or_create method that adds the is_active flag.

        :return the created/queried object
        """
        kwargs['is_active'] = True
        obj, created = cls.objects.get_or_create(*args, **kwargs)
        if not created:
            obj.prepare()

        return obj, created

    @classmethod
    def filter(cls, *args, **kwargs):
        """
        Wrapper over the standard filter method that adds the is_active flag.

        :param args: the anonymous query criteria
        :param kwargs: the named (key word) query criteria
        :return the filtered QuerySet object
        """
        kwargs['is_active'] = True
        filtered = cls.objects.filter(*args, **kwargs).order_by('created_at')
        filtered.exists()

        for obj in filtered:
            obj.prepare()

        return filtered

    def prepare(self):
        """
        Base method to be called before returning an object from db. Overridden in subclasses.
        """
        pass

    def get_absolute_url(self):
        """
        Base method for returning the object's absolute url. Overridden in subclasses.

        :return the object's absolute url
        """
        pass

    def get_name(self):
        """
        Base method for returning the object's name field value. Overridden in subclasses.

        :return the object's name field value
        """
        pass

    @staticmethod
    def get_type():
        """
        Base method for returning the object's data type in string format. Overridden in subclasses.

        :return the object's data type in string format
        """
        pass

    @staticmethod
    def link_to_admin(cls, pk):
        link = reverse(''.join(['admin:app_', cls, '_change']), args=[pk])
        return format_html('<a href="{}">{}</a>', link, pk)
