import string
from random import choice
print ''.join([choice(string.letters + string.digits + string.punctuation) for i in range(50)])
