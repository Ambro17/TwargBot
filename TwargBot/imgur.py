import requests
import config


class Imgur(object):
	POST_IMG_URL = "https://api.imgur.com/3/image"
	POST_ALBUM_URL = 'https://api.imgur.com/3/album'

	VIEW_ALBUM_URL = 'https://imgur.com/a'

	auth = {'authorization': f'Client-ID {config.IMGUR_KEY}'}

	def _upload_image(self, a_imgurl):
		# include in try except
		resp = requests.request("POST", self.POST_IMG_URL, data=a_imgurl, headers=self.auth)
		response = resp.json()

		if response['success']:
			return response['data']
		else:
			logger.error(f"Could not upload Image. Response status: {response['status']}")
			logger.error(response)
	
	def _upload_images(self, img_urls):
		return [self._upload_image(image_url) for image_url in img_urls]


	def _create_album(self, dhashes):
		resp = requests.request("POST", self.POST_ALBUM_URL, data={"deletehashes[]": dhashes}, headers=self.auth)
		adict = resp.json()
		
		if adict['status'] == 200:
			return adict['data']
		else:
			logger.error(f"Could not upload Album. Response status: {adict['status']}")
			logger.error(adict)
			return None

	def upload_images_to_album(self, img_urls):
		images = self._upload_images(img_urls)
		image_djashes = [image.get('deletehash') for image in images]
		album = self._create_album(image_djashes)
		album_link = f"{self.VIEW_ALBUM_URL}/{album['id']}"
		
		return album_link
