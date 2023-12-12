class Impossible(Exception):
    """Exceptions raised when an action is impossible to be performed
    The reason is given in the exception message
    """
class QuitWithoutSaving(SystemExit):
    """Can be raised to exit the game without automatically saving."""
class AutoQuit(Exception):
    """Exceptions raised when auto-action must stop."""      
class Dead(Exception):
    """Exceptions raised when player dies."""      
