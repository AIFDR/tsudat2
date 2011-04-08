from django.test.simple import DjangoTestSuiteRunner

class TsuDatTestSuiteRunner(DjangoTestSuiteRunner):

    # Override this method so we *dont* create a test database (use the normal one)
    def setup_databases(self, **kwargs):
        pass
    
    # Override this method so we dont drop the normal database
    def teardown_databases(self, old_config, **kwargs):
        pass
