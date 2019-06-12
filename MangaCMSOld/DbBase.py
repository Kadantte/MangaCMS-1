
import traceback
import abc
from contextlib import contextmanager
import MangaCMSOld.lib.LogBase
import threading
import MangaCMSOld.lib.dbPool
import traceback
import statsd
import settings

class TransactionMixin(object, metaclass=abc.ABCMeta):

	@contextmanager
	def transaction(self, commit=True):
		cursor = self.get_cursor()
		if commit:
			cursor.execute("BEGIN;")

		try:
			yield cursor

		except Exception as e:
			self.log.error("Error in transaction!")
			for line in traceback.format_exc().split("\n"):
				self.log.error(line)
			if commit:
				self.log.warn("Rolling back.")
				cursor.execute("ROLLBACK;")
			else:
				self.log.warn("NOT Rolling back.")

			raise e

		finally:
			if commit:
				cursor.execute("COMMIT;")
			self.release_cursor(cursor)

	@contextmanager
	def context_cursor(self):
		cursor = self.get_cursor()
		try:
			yield cursor
		finally:
			self.release_cursor(cursor)


	@abc.abstractmethod
	def get_cursor(self):
		return None

	@abc.abstractmethod
	def release_cursor(self, cursor):
		return None



# Minimal class to handle opening a DB interface.
class DbBase(MangaCMSOld.lib.LogBase.LoggerMixin, TransactionMixin, metaclass=abc.ABCMeta):

	# Abstract class (must be subclassed)
	__metaclass__ = abc.ABCMeta

	@abc.abstractmethod
	def loggerPath(self):
		return None
	@abc.abstractmethod
	def tableName(self):
		return None
	@abc.abstractmethod
	def pluginName(self):
		return None


	# @abc.abstractmethod
	# def siteName(self):
	# 	return None

	@abc.abstractmethod
	def pluginType(self):
		return None

	def __del__(self):
		for db_conn in self.db_connection_dict.values():
			try:
				db_conn.close()
			except Exception:
				pass

	def __init__(self):
		self.db_connection_dict = {}
		super().__init__()

		# self.mon_con = graphitesend.GraphitePickleClient(
		# 		autoreconnect   = True,
		# 		group           = None,
		# 		prefix          = 'MangaCMSOld.Scrapers.{tableName}.{pluginName}'.format(
		# 					tableName  = self.tableName.replace(".", "_"),
		# 					pluginName = self.pluginName.replace(".", "_")
		# 				),
		# 		system_name     = '',
		# 		graphite_server = settings.GRAPHITE_DB_IP,
		# 		graphite_port   = 2003,
		# 		debug           = True
		# 	)
		# self.mon_con.connect()
		if settings.GRAPHITE_DB_IP:

			prefix_str = 'MangaCMSOld.Scrapers.{tableName}.{loggerPath}'.format(
								tableName  = self.tableName.replace(".", "_").replace("-", "_").replace(" ", "_"),
								loggerPath = self.loggerPath.replace("-", "_").replace(" ", "_"),
							)

			self.log.info("Using graphite prefix str: '%s'", prefix_str)

			self.mon_con = statsd.StatsClient(
					host = settings.GRAPHITE_DB_IP,
					port = 8125,
					prefix = prefix_str
					)
		else:
			self.mon_con = None

	def __del__(self):
		if hasattr(self, 'db_connection_dict'):
			for conn in self.db_connection_dict:
				MangaCMSOld.lib.dbPool.pool.putconn(conn)

	@property
	def __thread_cursor(self):
		'''
		__getCursor and __freeConn rely on "magic" thread ID cookies to associate
		threads with their correct db pool interfaces
		'''

		tid = threading.get_ident()

		if tid in self.db_connection_dict:
			self.log.critical('Recursive access to singleton thread-specific resource!')
			self.log.critical("Calling thread ID: '%s'", tid)
			self.log.critical("Allocated handles")
			for key, value in self.db_connection_dict.items():
				self.log.critical("	'%s', '%s'", key, value)

			raise ValueError("Recursive cursor retreival! What's going on?")

		self.db_connection_dict[tid] = MangaCMSOld.lib.dbPool.pool.getconn()
		return self.db_connection_dict[tid].cursor()

	def __freeConn(self):
		conn = self.db_connection_dict.pop(threading.get_ident())
		MangaCMSOld.lib.dbPool.pool.putconn(conn)

	def get_cursor(self):
		return self.__thread_cursor

	def release_cursor(self, cursor):
		self.__freeConn()


class TestConn(DbBase):
	loggerPath = "TestConn"
	pluginName = "TestConn"
	tableName = "testDb"
	pluginType = "Utility"

def test_mon_con():
	c = TestConn()
	print(c)

	for newItems in range(5):
		# newItems = 9

		print("Doing send: ", c.mon_con, 'new_links', newItems)
		res = c.mon_con.incr('new_links_2', 1)
		print("Send return: ", res)
	pass



if __name__ == "__main__":
	test_mon_con()
