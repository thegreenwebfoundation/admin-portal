from django.contrib.auth.hashers import BCryptSHA256PasswordHasher


class BCrypt15Rounds(BCryptSHA256PasswordHasher):
    iterations = 15
