import pubcontrol
import gripcontrol

def is_proxied(request, proxies):
	if len(proxies) < 1:
		return False

	grip_sig = request.META.get('HTTP_GRIP_SIG')
	if not grip_sig:
		return False

	for p in proxies:
		if gripcontrol.validate_sig(grip_sig, p['key']):
			return True

	return False

class Publisher(object):
	def __init__(self):
		self.proxies = list()
		self.pubs = None

	def publish(self, channel, id, prev_id, rheaders=None, rbody=None, sbody=None, code=None, reason=None):
		if len(self.proxies) < 1:
			return

		if self.pubs is None:
			self.pubs = list()
			for p in self.proxies:
				pub = gripcontrol.GripPubControl(p['control_uri'])
				if 'control_iss' in p:
					pub.set_auth_jwt({'iss': p['control_iss']}, p['key'])
				self.pubs.append(pub)

		formats = list()
		if rbody is not None:
			formats.append(gripcontrol.HttpResponseFormat(code=code, reason=reason, headers=rheaders, body=rbody))
		if sbody is not None:
			formats.append(gripcontrol.HttpStreamFormat(sbody))

		item = pubcontrol.Item(formats, id, prev_id)

		for pub in self.pubs:
			pub.publish(channel, item)
