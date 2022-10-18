import logging
import os

# increasing workers uses more RAM, but provides a simple model for scaling up resources
workers = 8
# increasing threads saves RAM at the cost of using more CPU
threads = 1
