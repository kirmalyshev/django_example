try:
    import cPickle as pickle
except ImportError:
    import pickle
import redis


class SimpleRedisStorage:
    """
    Redis client to set/get value

    :param connection_data: redis connection data in format {'host': 'redis','port': 6379,'db': 11}
    :param key_prefix (optional): prefix key from all keys in the redis storage
    """

    _client = None
    key_prefix = ''

    def __init__(self, connection_data, key_prefix=None):
        self.connection_data = connection_data

        if key_prefix:
            self.key_prefix = key_prefix

    def unpickle(self, value):
        try:
            value = int(value)
        except (ValueError, TypeError):
            value = pickle.loads(value)
        return value

    def pickle(self, value):
        if isinstance(value, bool) or not isinstance(value, int):
            return pickle.dumps(value)
        return value

    @property
    def client(self):
        if self._client:
            return self._client

        if isinstance(self.connection_data, str):
            self._client = redis.from_url(self.connection_data)
        else:
            self._client = redis.Redis(**self.connection_data)
        return self._client

    def make_key(self, key):
        return f'{self.key_prefix}:{key}'

    def get(self, key, default=None):
        key = self.make_key(key)
        value = self.client.get(key)
        if value is None:
            return default
        res = self.unpickle(value)
        # self.close()
        return res

    def get_all_keys_iterator(self):
        """
        returns iterator with keys from db
        """
        return self.client.scan_iter()

    def delete(self, key):
        res = self.client.delete(self.make_key(key))
        # self.close()
        return res

    def set(self, key, value, timeout):
        """
        Set key to hold the value.

        :param timeout: key lifetime in storage (seconds)
        """
        key = self.make_key(key)
        value = self.pickle(value)
        if timeout > 0:
            return self.client.setex(key, int(timeout), value)

        result = self.client.set(key, value)
        # self.close()
        return result

    def clear(self):
        self.client.flushdb()
        # self.close()

    def close(self):
        if self._client:
            self._client.close()
            self._client = None
