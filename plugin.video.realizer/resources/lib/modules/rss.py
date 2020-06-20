from bs4 import BeautifulSoup
import requests
import datetime
import feedparser
import sys
import os
import urllib
from time import mktime
from resources.lib.modules import control, cleantitle
from resources.lib.api import debrid
try:
	from sqlite3 import dbapi2 as database
except:
	from pysqlite2 import dbapi2 as database
		
timeNow =  datetime.datetime.utcnow()
today = timeNow.strftime('%Y%m%d')
last3Days = (timeNow - datetime.timedelta(days=4)).strftime('%Y%m%d')

rssFile  = control.rssDb

rss_1_status = control.setting('rss.1')
rss_2_status = control.setting('rss.2')
rss_3_status = control.setting('rss.3')
rss_4_status = control.setting('rss.4')

rss_1 = control.setting('rss.link.1')
rss_1_offset = control.setting('rss.link.1.offset')
rss_2 = control.setting('rss.link.2')
rss_2_offset = control.setting('rss.link.2.offset')
rss_3 = control.setting('rss.link.3')
rss_3_offset = control.setting('rss.link.3.offset')
rss_4 = control.setting('rss.link.4')
rss_4_offset = control.setting('rss.link.4.offset')

rss_1_mode = control.setting('rss.1.mode')
rss_2_mode = control.setting('rss.2.mode')
rss_3_mode = control.setting('rss.3.mode')
rss_4_mode = control.setting('rss.4.mode')

def rssDB(data=None, mode='write', link=None, title=None):
	timeNow = datetime.datetime.utcnow()
	today = timeNow.strftime('%Y%m%d')
	
	dbcon = database.connect(rssFile)
	dbcon.text_factory = str
	dbcur = dbcon.cursor()
	
	if mode == 'write':
		try:
			dbcur.execute("CREATE TABLE IF NOT EXISTS rss (""title TEXT, ""link TEXT, ""id TEXT, ""added TEXT);")
		except:
			pass
		for item in data:
			dbcur.execute("INSERT INTO rss Values (?, ?, ?, ?)", (item['title'], item['link'], item['id'], today))
			dbcon.commit()
		
	elif mode == 'check': # CHECK MODE NEEDS LINK AND TITLE
		try:
			if link != '' and link != None:
				dbcur.execute("SELECT * FROM rss WHERE link = '%s'" % (link))
				match = dbcur.fetchone()
				if match: return True
			if title != '' and title != None:
				dbcur.execute("SELECT * FROM rss WHERE title = '%s'" % (title))
				match = dbcur.fetchone()			
				if match: return True
		except: return False
		return False
		
	elif mode == 'get': # CHECK MODE NEEDS LINK AND TITLE
		sources = []
		try:
			dbcur.execute("SELECT * FROM rss")
			match = dbcur.fetchall()
			for x in match:
				sources.append({'title': x[0], 'id': x[2], 'added': x[3]})
			return sources
		except: return sources
	elif mode == 'clear':
		try: os.remove(rssFile)
		except:pass
		try: os.remove(rssFile)
		except:pass	
		control.refresh()
		
			
def rssList():
	rssList = []
	if rss_1_status == 'true':
		if "http" in rss_1:
			if int(rss_1_mode) == 0: mode = 'cloud'
			else: mode = 'read'
			item = {'rss': rss_1, 'offset': str(rss_1_offset), 'mode': mode}
			rssList.append(item)
	if rss_2_status == 'true':			
		if "http" in rss_2:
			if int(rss_2_mode) == 0: mode = 'cloud'
			else: mode = 'read'
			item = {'rss': rss_2, 'offset': str(rss_2_offset), 'mode': mode}
			rssList.append(item)
	if rss_3_status == 'true':
		if "http" in rss_3:
			if int(rss_3_mode) == 0: mode = 'cloud'
			else: mode = 'read'
			item = {'rss': rss_3, 'offset': str(rss_3_offset), 'mode': mode}
			rssList.append(item)	
	if rss_4_status == 'true':
		if "http" in rss_4:
			if int(rss_4_mode) == 0: mode = 'cloud'
			else: mode = 'read'
			item = {'rss': rss_4, 'offset': str(rss_4_offset), 'mode': mode}
			rssList.append(item)
	return rssList
		
def update():
	VALID_EXT = debrid.VALID_EXT
	rsslist = rssList()
	rsslist = [i for i in rsslist if i['mode'] != 'read']
	sourceList = []
	if len(rsslist) > 0: control.infoDialog('Checking RSS Lists...')
	for x in rsslist:
		u = x['rss']
		timeNow =  datetime.datetime.utcnow()
		timeOffset = int(x['offset'])
		timeOffset = (timeNow - datetime.timedelta(days=int(timeOffset))).strftime('%Y%m%d')
		
		html = feedparser.parse(u)
		rssEntries = html.entries
		try:
		    rssTitle = html['feed']['title']
		except:
		    rssTitle = html['feed']

		for item in rssEntries:
			try:

				title = item.title
				link  = item.link
				dateString = item.published_parsed
				
				checkDB = rssDB(mode='check', link=link, title=title)
				
				if checkDB == True: 
					print ("[REALIZER RSS MANAGER] TORRENT ALREADY ADDED: %s" % title)
					raise Exception()

				dt = datetime.datetime.fromtimestamp(mktime(dateString))
				pubDate = dt.strftime('%Y%m%d')
				strDate = dt.strftime('%Y-%m-%d')				
				if int(pubDate) >= int(timeOffset):
					r = debrid.realdebrid().addtorrent(link)
					id = r['id']
					select = debrid.realdebrid().torrentInfo(id)
					
					status = str(select['status'])
					print ("[REALIZER RSS MANAGER] REALDEBRID STATUS", status)
					if cleantitle.get(status) != 'waitingfilesselection' and cleantitle.get(status) != 'downloaded': 
						debrid.realdebrid().delete(id, type = 'torrents')
						raise Exception()					
					
					
					files = select['files']
					filesIDs = [i['id'] for i in files if i['path'].split('.')[-1].lower() in VALID_EXT]
					if len(filesIDs) < 1 or filesIDs == []:
						debrid.realdebrid().delete(id, type = 'torrents')
						raise Exception()					
					r = debrid.realdebrid().selectTorrentList(id, filesIDs)
					source = {'title': title, 'link': link , 'id': id, 'date': str(strDate)}
					sourceList.append(source)
			except: pass
	control.infoDialog('RSS Lists check completed')
	rssDB(data=sourceList)

def reader_cat():
	sysaddon = sys.argv[0]
	syshandle = int(sys.argv[1])
	VALID_EXT = debrid.VALID_EXT
	rsslist = rssList()
	rsslist = [i for i in rsslist]
	try:
		for x in rsslist:
			link = x['rss']
			u = link.split("//")[-1].split("/")[0].split('?')[0]
			title = u

			label = title
			item = control.item(label=label)					
			item.setArt({'icon': control.addonIcon()})
			item.setProperty('Fanart_Image', control.addonFanart())
			infolabel = {"Title": label}
			url = '%s?action=%s&id=%s' % (sysaddon, 'rss_reader', link) 
			control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)	
	except:pass
				
	control.directory(syshandle, cacheToDisc=True)	

	
def reader(url):
	sysaddon = sys.argv[0]
	syshandle = int(sys.argv[1])
	VALID_EXT = debrid.VALID_EXT

	try:
			html = feedparser.parse(url)
			rssEntries = html.entries
			for item in rssEntries:
				try:

					title = item.title
					link  = item.link
					
					label = title
					item = control.item(label=label)					
					item.setArt({'icon': control.addonIcon()})
					item.setProperty('Fanart_Image', control.addonFanart())
					infolabel = {"Title": label}
					url = '%s?action=%s&id=%s' % (sysaddon, 'rdAddTorrent', urllib.quote_plus(link)) 
					control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)	

				except:pass
	except:pass
				
	control.directory(syshandle, cacheToDisc=True)

	

	
def manager():
	sysaddon = sys.argv[0]
	syshandle = int(sys.argv[1])
	VALID_EXT = debrid.VALID_EXT
	updt = '%s?action=%s' % (sysaddon, 'rss_update')
	item = control.item(label='[UPDATE NOW]')
	control.addItem(handle=syshandle, url=updt, listitem=item, isFolder=False)
	clear = '%s?action=%s' % (sysaddon, 'rss_clear')
	item = control.item(label='[CLEAR DATABASE]')
	control.addItem(handle=syshandle, url=clear, listitem=item, isFolder=False)
	try:
		r  = rssDB(mode='get')
		try: r = sorted(r, key=lambda x: int(x['added']), reverse=True)
		except: pass
		for item in r:
			try:
				cm = []
				date = item['added']

				id = item['id']
				name = item['title']
				label = date + " | " + name
				item = control.item(label=label)
				item.setArt({'icon': control.addonIcon()})
				item.setProperty('Fanart_Image', control.addonFanart())
				infolabel = {"Title": label}
				cm.append(('Delete Torrent Item', 'RunPlugin(%s?action=rdDeleteItem&id=%s&type=torrents)' % (sysaddon, id)))
				url = '%s?action=%s&id=%s' % (sysaddon, 'rdTorrentInfo', id) 
				item.addContextMenuItems(cm)
				control.addItem(handle=syshandle, url=url, listitem=item, isFolder=True)
			except:pass
	except:pass
				
	control.directory(syshandle, cacheToDisc=True)

	