import unittest
import random
from datastore import Datastore


class TestDatastore(unittest.TestCase):

    def test_store_key_value(self):
        key = "test_key"
        value = random.random()

        Datastore().delete(key)
        Datastore().store(key, value)
        self.assertEqual(str(value), Datastore().get(key))

    def test_store_hash(self):
        key = "test_hash"
        value = {"a": random.random(), "b": random.random()}

        Datastore().delete(key)
        Datastore().store(key, value)

        for k in value:
            self.assertEqual(str(value[k]), Datastore().get(key, k))

    def test_store_list(self):
        list_name = "test_list"
        items = [1, 2, 3, 4, 5]

        Datastore().trim_list(list_name)

        Datastore().store_to_list(list_name, *items)
        stored_items = Datastore().get_range(list_name, len(items))

        # data is stored to top
        for index, item in enumerate(items[::-1]):
            self.assertEqual(str(item), stored_items[index])
