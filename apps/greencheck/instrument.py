import inspect
import logging

from collections.abc import Callable
from functools import wraps
from timeit import default_timer as timer
from typing import Any

def instrument(label : str, lookup_key : str):
    """This is a decorator used to log timings for the different phases of
    a domain check.We provide a descriptive label to annotate the log line,
    and the execution time is logged, along with details of what was being
    looked up, (a domain or ip), given by the argument to the original
    function named by lookup_key.
    """
    def instrument_generator(old_function : Callable) -> Callable:
        sig = inspect.signature(old_function)
        @wraps(old_function)
        def new_function(self, *args, **kwargs) -> Any:
            # The use of Signature.bind allows us to get the argument
            # referred to by lookup_key irrespective of it it was passed
            # as an arg or a kwarg
            bound_args = sig.bind(self, *args, **kwargs)
            bound_args.apply_defaults()
            lookup_value = bound_args.arguments[lookup_key]
            start = timer()
            result = old_function(self, *args, **kwargs)
            duration = timer() - start
            # We get the logger INSIDE the wrapped function to ensure
            # the original __name__ is preserved:
            logger = logging.getLogger(__name__)
            logger.info(
                    f"Metrics: {label} for {lookup_value} took {duration:.4f}s"
            )
            return result
        return new_function
    return instrument_generator
