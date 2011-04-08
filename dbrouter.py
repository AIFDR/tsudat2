class GeoNodeRouter(object):
    def db_for_read(self, model, **hints):
        "Point all operations on geonode models to 'geonode'"
        if model._meta.app_label in ['maps','core']:
            return 'geonode'
        return None

    def db_for_write(self, model, **hints):
        "Point all operations on geonode models to 'geonode'"
        if model._meta.app_label in ['maps','core']:
            return 'geonode'
        return None

    def allow_relation(self, obj1, obj2, **hints):
        "Allow any relation if a model in geonode is involved"
        if obj1._meta.app_label in ['maps','core'] or obj2._meta.app_label in ['maps','core']:
            return True
        return None

    def allow_syncdb(self, db, model):
        "Make sure the geonode app only appears on the 'geonode' db"
        if db == 'geonode':
            return model._meta.app_label in ['maps','core']
        elif model._meta.app_label in ['maps','core']:
            return False
        return None
