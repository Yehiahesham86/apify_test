class FilteringData:
    filter_words = (
        'linkedin', 'wa.me', 'whatsapp', 'iwtsp.com', 'facebook', 'twitter', 'instagram', 'pinterest',
        'youtube', 'tiktok', 'onelink', 'reddit', 'snapchat', 'tumblr', 'telegram', 'yelp', 'discord', 'threads',
        'messenger.com', 'booking.com',
        'medium', 'quora', 'flickr', 'vimeo', 'dailymotion', 'soundcloud', 'spotify', 'dribbble', 'behance', 'github',
        'gitlab', 'bitbucket',
        'stackexchange', 'stackoverflow', 'goodreads', 'rottentomatoes', 'imdb', 'tripadvisor', 'airbnb', 'expedia',
        'skyscanner', 'kayak', 'agoda'
    )

    def filter_link(self, url):
        new_url = url.lower()
        for word in self.filter_words:
            if word in new_url:
                return {
                    'url': url,
                    'error': f"We do not process {word} in this API!"
                }
