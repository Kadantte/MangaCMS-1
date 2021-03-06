


import re
import yaml
import json

import time

import runStatus
import settings
import pickle


import MangaCMSOld.ScrapePlugins.M.IrcGrabber.IrcQueueBase


class TriggerLoader(MangaCMSOld.ScrapePlugins.M.IrcGrabber.IrcQueueBase.IrcQueueBase):



	loggerPath = "Main.Manga.Vi.Fl"
	pluginName = "Recent XdccParser Link Retreiver"
	tableKey = "irc-irh"
	dbName = settings.DATABASE_DB_NAME


	tableName = "MangaItems"

	feedUrls = [
		("http://vi-scans.com/bort/search.php",                  "viscans")
	]

	extractRe = re.compile(r"p\.k\[\d+\] = ({.*?});")


	def getPacklist(self, url, channel):
		page = self.wg.getpage(url)
		page = page.strip()
		matches = self.extractRe.findall(page)
		yamlData = "[%s]" % (", ".join(matches))

		# we need to massage the markup a bit to make it parseable by PyYAML.
		# Basically, the raw data looks like:
		# {b:"Suzume", n:2180, s:7, f:"Chinatsu_no_Uta_ch23_[VISCANS].rar"};
		# but {nnn}:{nnn} is not valid, YAML requires a space after the ":"
		# Therefore, we just replace ":" with ": "
		yamlData = yamlData.replace(":", ": ")

		self.log.info("Doing YAML data load")
		data = yaml.load(yamlData, Loader=yaml.CLoader)

		ret = []
		for item in data:
			item["server"] = "irchighway"
			item["channel"] = channel

			# rename a few keys that are rather confusing
			item["size"] = item.pop("s")
			item["pkgNum"] = item.pop("n")
			item["botName"] = item.pop("b")
			item["fName"] = item.pop("f")

			# I'm using the filename+botname for the unique key to the database.
			itemKey = item["fName"]+item["botName"]

			item = json.dumps(item)

			ret.append((itemKey, item))

			if not runStatus.run:
				self.log.info( "Breaking due to exit flag being set")
				break


		self.log.info("Found %s items", len(ret))
		return ret


	def getMainItems(self, rangeOverride=None, rangeOffset=None):
		# for item in items:
		# 	self.log.info( item)
		#

		self.log.info( "Loading ViScans Main Feed")

		ret = []
		for packUrl, chan in self.feedUrls:
			ret += self.getPacklist(packUrl, chan)

		self.log.info("Complete. Total items: %s", len(ret))
		return ret






if __name__ == "__main__":
	import MangaCMSOld.lib.logSetup
	MangaCMSOld.lib.logSetup.initLogging()
	fl = TriggerLoader()
	# print(fl)
	# fl.getMainItems()

	fl.go()





