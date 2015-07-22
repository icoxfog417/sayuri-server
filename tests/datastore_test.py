import unittest
import random
from sayuri.datastore import Datastore


class TestDatastore(unittest.TestCase):

    def test_store_key_value(self):
        key = "test_key"
        value = random.random()
        db = Datastore("test_schema")

        db.delete(key)
        db.store(key, value)
        self.assertEqual(str(value), db.get(key))

    def test_store_hash(self):
        key = "test_hash"
        value = {"a": random.random(), "b": random.random()}
        db = Datastore("test_schema")

        db.delete(key)
        db.store(key, value)

        for k in value:
            self.assertEqual(str(value[k]), db.get(key, k))

    def test_store_list(self):
        list_name = "test_list"
        items = [1, 2, 3, 4, 5]
        db = Datastore("test_schema")

        db.trim_list(list_name)

        db.store_to_list(list_name, *items)
        stored_items = db.get_list(list_name, len(items))

        # data is stored to top
        for index, item in enumerate(items[::-1]):
            self.assertEqual(str(item), stored_items[index])
