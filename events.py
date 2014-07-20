
class OnEvents(object):
    """ """
    def __init__(self):
        self.success_hooks = []
        self.failure_hooks = []
        self.exit_hooks = []

    def on_success(self, *args, **kwargs):
        pass

    def call_success_hooks(self, *args, **kwargs):
        while self.success_hooks:
            hook = self.success_hooks.pop()
            hook(*args, **kwargs)

    def on_failure(self, *args, exception=None, **kwargs):
        runtimeerror = RuntimeError('An error occurred executing ' + 
                                    self.__class__.__name__)
        if exception:
            raise runtimeerror from exception
        else:
            raise runtimeerror

    def call_failure_hooks(self, *args, **kwargs):
        while self.failure_hooks:
            hook = self.failure_hooks.pop()
            hook(*args, **kwargs)

    def on_exit(self, *args, **kwargs):
        pass

    def call_exit_hooks(self, *args, **kwargs):
        while self.exit_hooks:
            hook = self.exit_hooks.pop()
            hook(*args, **kwargs)

    def event_trigger(self, event, *args, **kwargs):
        try:
            if event == True:
                try:
                    self.on_success(*args, **kwargs)
                except (Exception, BaseException):
                    raise
                finally:
                    self.call_success_hooks(*args, **kwargs)
            elif event == False:
                try:
                    self.call_failure_hooks(*args, **kwargs)
                except (Exception, BaseException):
                    raise
                finally:
                    self.on_failure(*args, **kwargs)
        except:
            raise
        finally:
            try:
                self.on_exit(*args, **kwargs)
            except (Exception, BaseException):
                raise
            finally:
                self.call_exit_hooks(*args, **kwargs)

    
def handle_events(f):
    def on_event(self, *args, **kwargs):
        try:
            f(self, *args, **kwargs)
        except (Exception, BaseException) as e:
            try:
                self.call_failure_hooks(*args, **kwargs)
            except (Exception, BaseException):
                raise
            finally:
                self.on_failure(*args, exception=e, **kwargs)
        else:
            try:
                self.on_success(*args, **kwargs)
            except (Exception, BaseException):
                raise
            finally:
                self.call_success_hooks(*args, **kwargs)
        finally:
            try:
                self.on_exit(*args, **kwargs)
            except (Exception, BaseException):
                raise
            finally:
                self.call_exit_hooks(*args, **kwargs)
    return on_event

