"""
Characters

Characters are (by default) Objects setup to be puppeted by Accounts.
They are what you "see" in game. The Character class in this module
is setup to be the "default" character type created by the default
creation commands.

PLATO FIX (JC1): Account permissions (Builder, Developer, Admin) are
propagated to the character object on puppet. This ensures @dig, @create,
@py and other builder commands work when the account has the permission.

Root cause: Evennia 4.5.0 cmd locks check against the CHARACTER object's
permissions, not the account's. So granting Builder to AccountDB doesn't
unlock @dig for the puppeted character.

Fix location: typeclasses/characters.py
Applies to: Evennia 4.5.0+
"""

from evennia.objects.objects import DefaultCharacter

from .objects import ObjectParent

# Permissions that should flow from account to character
_PROPAGATED_PERMS = {"Builder", "Developer", "Admin", "Immortals", "Wizards"}


class Character(ObjectParent, DefaultCharacter):
    """
    The Character just re-implements some of the Object's methods and hooks
    to represent a Character entity in-game.

    See mygame/typeclasses/objects.py for a list of
    properties and methods available on all Object child classes like this.

    """

    def at_post_puppet(self, **kwargs):
        """
        Called after a puppet session is established.
        Sync account permissions to the character object.
        """
        super().at_post_puppet(**kwargs)
        self._sync_account_permissions()

    def _sync_account_permissions(self):
        """Copy relevant permissions from account to character."""
        account = self.account
        if not account or not hasattr(account, 'permissions'):
            return
        changed = False
        for perm in account.permissions.all():
            if perm in _PROPAGATED_PERMS and perm not in self.permissions.all():
                self.permissions.add(perm)
                changed = True
        if changed:
            self.save(update_fields=["db_perm__list"])
