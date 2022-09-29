import time
from django.core.management.base import BaseCommand
from api.util import expire_inboxes, expire_items, expire_requests

class Command(BaseCommand):
	help = 'Background cleanup task'

	def handle(self, *args, **options):
		inboxes = expire_inboxes()
		print('expired %d inboxes' % inboxes)

		# expire items of remaining inboxes
		items, inboxes = expire_items()
		print('expired %d items in %d active inboxes' % (items, inboxes))

		# we expect this command to run once per minute, so to achieve
		#   a 10 second interval, we'll do 6 iterations within a
		#   single run
		for n in range(0, 6):
			if n != 0:
				time.sleep(10)
			requests = expire_requests()
			print('expired %d requests' % requests)
