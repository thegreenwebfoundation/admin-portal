from django.contrib.auth.hashers import BCryptSHA256PasswordHasher


class LegacyBCrypt(BCryptSHA256PasswordHasher):
    algorithm = 'legacy_bcrypt'
    iterations = 15
    digest = None
