
class OnEvents(object):
    """ """
    def __init__(self):
        self.success_hooks = []
        self.failure_hooks = []
        self.exit_hooks = []

    def on_success(self, **kwargs):
        pass

    def on_failure(self, exception=None, **kwargs):
        runtimeerror = RuntimeError('An error occurred executing ' + 
                                    self.__class__.__name__)
        if exception:
            raise runtimeerror from exception
        else:
            raise runtimeerror

    def on_exit(self, **kwargs):
        pass

    def event_trigger(self, event, *args, **kwargs):
        try:
            if event == True:
                try:
                    self.on_success(**kwargs)
                except (Exception, BaseException):
                    raise
                finally:
                    while self.success_hooks:
                        hook = self.success_hooks.pop()
                        hook(*args, **kwargs)
            elif event == False:
                try:
                    while self.failure_hooks:
                        hook = self.failure_hooks.pop()
                        hook(*args, **kwargs)
                except (Exception, BaseException):
                    raise
                finally:
                    self.on_failure()
        except:
            raise
        finally:
            try:
                self.on_exit(**kwargs)
            except (Exception, BaseException):
                raise
            finally:
                while self.exit_hooks:
                    hook = self.exit_hooks.pop()
                    hook(*args, **kwargs)
    
def handle_events(f):
    def on_event(self, *args, **kwargs):
        try:
            f(self, *args, **kwargs)
        except (Exception, BaseException) as e:
            try:
                while self.failure_hooks:
                    hook = self.failure_hooks.pop()
                    hook(*args, **kwargs)
            except (Exception, BaseException):
                raise
            finally:
                self.on_failure(exception=e)
        else:
            try:
                self.on_success(**kwargs)
            except (Exception, BaseException):
                raise
            finally:
                while self.success_hooks:
                    hook = self.success_hooks.pop()
                    hook(*args, **kwargs)
        finally:
            try:
                self.on_exit(**kwargs)
            except (Exception, BaseException):
                raise
            finally:
                while self.exit_hooks:
                    hook = self.exit_hooks.pop()
                    hook(*args, **kwargs)
    return on_event
