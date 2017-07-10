import json
import time
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, Filters,CallbackQueryHandler, RegexHandler, Job, JobQueue
import os
import logging
import json
import urllib
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from random import randint
import pymongo
from telegram.chataction import ChatAction
import boto3
import requests
import urllib2
import shutil


print os.environ['AWS_ACCESS_KEY_ID']


s3 = boto3.client(
    's3',
    aws_access_key_id = os.environ['AWS_ACCESS_KEY_ID'],
    aws_secret_access_key = os.environ['AWS_SECRET_ACCESS_KEY']
)
next_keyboard = ReplyKeyboardMarkup([[KeyboardButton("next")]], resize_keyboard=True)


start_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("start", callback_data='start')]])

start_keyboard2 = InlineKeyboardMarkup([[InlineKeyboardButton("beginning", callback_data='start'),InlineKeyboardButton("resume", callback_data='resume')]])

archive_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("archive", callback_data='archive'),InlineKeyboardButton("restart", callback_data='start')]])

resume_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("resume", callback_data='resume')]])

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


SETTITLEPUSH,ADDTERMORDONE,NEXT,STARTPOINT= range(4)

logger = logging.getLogger(__name__)
client = pymongo.MongoClient(os.environ['MONGODB_URI'])

db = client.get_default_database()

users = db['users']
collections = db['collections']
archive = db['archive']


userformat = {
              "collection_ids":[],
              "id":None,
              "currentSetCollection":[],
              "currentReadCollection":None
              }

collectionformat = {
              "title":None,
              "user_id":None,
              "id":None,
              "collection":None,
              "index":0
              }



def find_collection(collections, collection_id):
    for i in range(len(collections)):
        if collections[i].collection_id == collection_id:
            return i
    return None

def start(bot, update):
    user = users.find_one({"id":update.message.chat.id})
    if user != None:
        update.message.reply_text("you are already registered")
        return
    bot.sendChatAction(update.message.chat.id, ChatAction.TYPING)
    time.sleep(1)
    update.message.reply_text("Hi")
    user2add = {
              "collection_ids":[],
              "id":None,
              "currentSetCollection":[],
              "currentReadCollection":None
              }
    user2add['id']=update.message.chat.id
    users.insert_one(user2add)



def help(bot, update):
    update.message.reply_text('Send Location and I will tell you trends near you')

def error(bot, update, error):
    
    logger.warn('Update "%s" caused error "%s"' % (update, error))


    
def menuButtons(bot,update):
    query = update.callback_query.id
    queryObj = update.callback_query
    queryData = update.callback_query.data
    print update
    print update.callback_query.message.chat.id
    try:
        user = users.find_one({"id":queryObj.message.chat.id})
    except:
        queryObj.message.reply_text("You are not registered. Press /start and then resend command2")
        return
    print user


    mid = queryObj.message.message_id
    message=update.callback_query.message.text
    messageComponents=message.split('\n')
    noteidline = messageComponents[0]
    collid= noteidline[4:]
    intcollid = int(collid)

    if str(queryData) == 'start':
        print "start"
        collections.update({"id":intcollid,"user_id":user["id"]},{"$set":{"index":0}})
        
        collection = collections.find_one({"id":intcollid,"user_id":user["id"]})
        print collection
        users.update({"id":user["id"]},{"$set":{"currentReadCollection":collection['id']}})
        queryObj.message.reply_text(collection['collection'][collection['index']])
        collections.update({"id":intcollid,"user_id":user["id"]},{"$inc":{"index":1}})
        collection = collections.find_one({"id":intcollid,"user_id":user["id"]})
        
        if collection['index']==len(collection['collection']):
            collections.update({"id":intcollid,"user_id":user["id"]},{"$set":{"index":0}})
            queryObj.message.reply_text("COLL"+str(collection['id'])+'\n'+'\n'+"You have reached the end of this reading",reply_markup=archive_keyboard)
            return
        return

    if str(queryData) == 'resume':
        print "resume"
        collection = collections.find_one({"id":intcollid,"user_id":user["id"]})
        print collection
        if collection==None:
            queryObj.message.reply_text('collection not found')
            return

        users.update({"id":user["id"]},{"$set":{"currentReadCollection":collection['id']}})
        queryObj.message.reply_text(collection['collection'][collection['index']],reply_markup=next_keyboard)
        collections.update({"id":intcollid,"user_id":user["id"]},{"$inc":{"index":1}})
        collection = collections.find_one({"id":intcollid,"user_id":user["id"]})
        print collection

        queryObj.message.reply_text(collection['collection'][collection['index']])
        if collection['index']==len(collection['collection']):
            print "if branch"
            collections.update({"id":intcollid,"user_id":user["id"]},{"$set":{"index":0}})
            queryObj.message.reply_text("COLL"+str(collection['id'])+'\n'+'\n'+"You have reached the end of this reading",reply_markup=archive_keyboard)
            return
        return
    if str(queryData) == 'archive':
        print 'archive'
        collection = collections.find_one({"id":intcollid,"user_id":user["id"]})
        print collection
        archive.insert_one(collection)
        collection_ids = user['collection_ids']
        collection_ids.remove(intcollid)
        users.update({"id":user['id']},{"$set":{"collection_ids":collection_ids}})
        collections.delete_one({"id":intcollid,"user_id":user["id"]})
        queryObj.message.reply_text("Collection Archived"+'\n'+'\n'+"<b>Restore Link: </b>"+'/restore'+str(intcollid),parse_mode="HTML")
        print "hello"
        return








def addTerm(bot,update):
    update.message.reply_text(os.environ['aws_access_key_id'])

    try:        
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return

    users.update({"id":user['id']},{"$push":{"currentSetCollection":update.message.text}})
    update.message.reply_text("/push")
    return


def addAudio(bot,update):
    print update
    file_id= update.message.audio.file_id
    url = bot.getFile(file_id).file_path
##    s3.upload_file("a.txt","scribenotetakingbot","b.txt")
##    aws_base_url ="https://s3-us-west-1.amazonaws.com/scribenotetakingbot/"
    print url

def addVoice(bot,update):
    print update
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return
    file_id= update.message.voice.file_id
    url = bot.getFile(file_id).file_path
    print url
    urlComps = url.split('/')
    fileName= urlComps[-1]
    fileobj = requests.get(url, stream = True)
    fileact=fileobj.raw
    with open(fileName, 'wb') as location:
        shutil.copyfileobj(fileact, location)
    del fileact
    s3.upload_file(fileName,"scribenotetakingbot",fileName)
    url ="https://s3-us-west-1.amazonaws.com/scribenotetakingbot/"+fileName
    users.update({"id":user['id']},{"$push":{"currentSetCollection":url}})
    os.remove(fileName)
    update.message.reply_text("/push")
    return


def addPhoto(bot,update):
    print update
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return
    file_id= update.message.photo[0]['file_id']
    url = bot.getFile(file_id).file_path
    print url
    urlComps = url.split('/')
    fileName= urlComps[-1]
    print fileName
    fileobj = requests.get(url, stream = True)
    fileact=fileobj.raw
    with open(fileName, 'wb') as location:
        shutil.copyfileobj(fileact, location)
    del fileact
    s3.upload_file(fileName,"scribenotetakingbot",fileName)
    url ="https://s3-us-west-1.amazonaws.com/scribenotetakingbot/"+fileName
    users.update({"id":user['id']},{"$push":{"currentSetCollection":url}})
    os.remove(fileName)
    update.message.reply_text("/push")
    return
    


def addVideo(bot,update):
    print update
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return
    print update
    file_id= update.message.video.file_id
    url = bot.getFile(file_id).file_path
    print url
    urlComps = url.split('/')
    fileName= urlComps[-1]
    fileobj = requests.get(url, stream = True)
    fileact=fileobj.raw
    with open(fileName, 'wb') as location:
        shutil.copyfileobj(fileact, location)
    del fileact
    s3.upload_file(fileName,"scribenotetakingbot",fileName)
    url ="https://s3-us-west-1.amazonaws.com/scribenotetakingbot/"+fileName
    users.update({"id":user['id']},{"$push":{"currentSetCollection":url}})
    os.remove(fileName)
    update.message.reply_text("/push")
    return
def done(bot,update):
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END
    update.message.reply_text("What do you want to call this collection?")
    return SETTITLEPUSH


def setTitlePush(bot,update):
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END
    
    collection_id = randint(10000,99999)
    while collection_id in user['collection_ids']:
        collection_id = randint(10000,99999)
    collection = {
              "title":update.message.text,
              "user_id":update.message.chat.id,
              "id":collection_id,
              "collection":user['currentSetCollection'],
              "index":0
              }
    collections.insert_one(collection)
    users.update({"id":update.message.chat.id},{"$set":{"currentSetCollection":[]}})
    users.update({"id":update.message.chat.id},{"$push":{"collection_ids":collection_id}})
    
    update.message.reply_text("Collection set!")
    if collection['index']==0:
        keyboard = start_keyboard
    else:
        keyboard = start_keyboard2

    update.message.reply_text("COLL"+str(collection['id'])+'\n'+'\n'+collection['title'], reply_markup=keyboard)
    return ConversationHandler.END

def cancelPush(bot,update):
    update.message.reply_text("Alright... to clear the current selection use /clear")
    return ConversationHandler.END


def clear(bot,update):
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return 

    users.update({"id":user['id']},{"$set":{"currentSetCollection":[]}})
    update.message.reply_text("collection cleared")
    return


    

def mycollections(bot,update):
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END

    collectionsList= list(collections.find({"user_id":update.message.chat.id}))

    string = 'COLLECTIONS'+'\n'+'\n'

    for i in collectionsList:
        string = string+i['title']+'\n'+"View Link: "+'/read'+str(i['id'])+'\n'+'\n'
    update.message.reply_text(string)
    return



def read(bot,update):
    print update
    try:
        user = users.find_one({"id":update.message.chat.id})
        print user
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END
    text = update.message.text
    text = text[5:]
    collid = int(text)
    if collid not in user['collection_ids']:
        bot.sendChatAction(update.message.chat.id, ChatAction.TYPING)
        time.sleep(1)
        update.message.reply_text("Can't find the collection... have you archived it already?", reply_markup=ReplyKeyboardRemove())
        return
                       
    collection = collections.find_one({'user_id':update.message.chat.id,"id":collid})
    print collection
    if collection ==None:
        bot.sendChatAction(update.message.chat.id, ChatAction.TYPING)
        time.sleep(1)
        update.message.reply_text("Can't find the collection... have you archived it already?", reply_markup=ReplyKeyboardRemove())
        return
    if collection['index']==0:
        keyboard = start_keyboard
    else:
        keyboard = start_keyboard2

    update.message.reply_text("COLL"+str(collection['id'])+'\n'+'\n'+collection['title'], reply_markup=keyboard)

    return

def archivef(bot,update):
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END
    text = update.message.text
    text = text[9:]
    collid = int(text)
    if collid not in user['collection_ids']:
        bot.sendChatAction(update.message.chat.id, ChatAction.TYPING)
        time.sleep(1)
        update.message.reply_text("Can't find the collection... have you archived it already?", reply_markup=ReplyKeyboardRemove())
        return
                       
    collection = collections.find_one({"id":collid,"user_id":user["id"]})
    collection['index']=None
    archive.insert_one(collection)
    collection_ids = user['collection_ids']
    collection_ids.remove(collid)
    users.update({"id":user['id']},{"$set":{"collection_ids":collection_ids}})
    collections.delete_one({"id":collid,"user_id":user["id"]})
    update.message.reply_text("Collection Archived"+'\n'+'\n'+"<b>Restore Link: </b>"+'/restore'+str(collid),parse_mode="HTML")
    return

def restore(bot,update):
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END
    text = update.message.text
    text = text[8:]
    collid = int(text)
          
    collection = archive.find_one({"id":collid,"user_id":user["id"]})
    if not collection:
        bot.sendChatAction(update.message.chat.id, ChatAction.TYPING)
        time.sleep(1)
        update.message.reply_text("Can't find the collection... have you archived it already?", reply_markup=ReplyKeyboardRemove())
        return
    archive.delete_one({"id":collid,"user_id":user["id"]})
    collection_ids = user['collection_ids']
    if collection['id'] in collection_ids:
        collection_id = randint(10000,99999)
        while collection_id in user['collection_ids']:
            collection_id = randint(10000,99999)
        collection['id']=collection_id
        
    collections.insert_one(collection)
    collection_ids.append(collection['id'])
    users.update({"id":user['id']},{"$set":{"collection_ids":collection_ids}})
    update.message.reply_text("Collection restored!")
    print collection['title']
    collection=collections.find_one({"id":collection['id'],"user_id":user["id"]})
    update.message.reply_text("COLL"+str(collection['id'])+'\n'+'\n'+collection['title'],reply_markup=start_keyboard)
    return 


def nextSeg(bot,update):
    print "nextSeg reached"
    try:
        user = users.find_one({"id":update.message.chat.id})
        print "user found"
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END
    
    if update.message.text=="next":
        print "next branch activated"
        collection = collections.find_one({"id":user['currentReadCollection'],"user_id":update.message.chat.id})
        
        if collection['index']==len(collection['collection']):
            collections.update({"id":user['currentReadCollection'],"user_id":user["id"]},{"$set":{"index":0}})
            update.message.reply_text("You have reached the end of this collection")
            update.message.reply_text("COLL"+str(collection['id']),reply_markup=archive_keyboard)
            return ConversationHandler.END
        

                
        print "hi"
        update.message.reply_text(collection['collection'][collection['index']],reply_markup=next_keyboard)
        collections.update({"id":user['currentReadCollection'],"user_id":update.message.chat.id},{"$inc":{"index":1}})
        return

    if update.message.text=="exit":
        users.update({"user_id":update.message.chat.id},{"$set":{"currentReadCollection":None}})
        update.message.reply_text("COLL"+str(collection['id'])+'\n'+'\n'+"You have exited this reading",reply_markup=resume_keyboard)
        return ConversationHandler.END

def main():
    # Create the EventHandler and pass it your bot's token.
    TOKEN = os.environ['BOT_TOKEN']
    updater = Updater(TOKEN)
    PORT = int(os.environ.get('PORT', '5000'))
    # job_q= updater.job_queue

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))
    dp.add_handler(CommandHandler("collections",mycollections))
    dp.add_handler(RegexHandler("^/read",read))
    dp.add_handler(RegexHandler("^/archive",archivef))
    dp.add_handler(RegexHandler("^/restore",restore))
    dp.add_handler(CallbackQueryHandler(menuButtons))


    
    pushhandler = ConversationHandler(
    entry_points=[CommandHandler("push",done)],
    states={
        SETTITLEPUSH: [RegexHandler("^cancel?",cancelPush),
                       MessageHandler(Filters.text,setTitlePush)
                  ]
    },

    fallbacks=[RegexHandler('^cancel$', help)]
    )
    dp.add_handler(pushhandler)

    dp.add_handler(RegexHandler("^next?",nextSeg))


    dp.add_handler(MessageHandler(Filters.text,addTerm))
    dp.add_handler(MessageHandler(Filters.photo,addPhoto))
    dp.add_handler(MessageHandler(Filters.audio,addAudio))
    dp.add_handler(MessageHandler(Filters.voice,addVoice))
    dp.add_handler(MessageHandler(Filters.video,addVideo))
    


    dp.add_handler(RegexHandler("^exit?",nextSeg))
    dp.add_handler(CommandHandler("clear",clear))



    # log all errors
    dp.add_error_handler(error)

    # Start the Bot

##    updater.start_polling()
    updater.start_webhook(listen="0.0.0.0",
                      port=PORT,
                      url_path=TOKEN)
    updater.bot.set_webhook("https://notetakingbot.herokuapp.com/" + TOKEN)
    updater.idle()


if __name__ == '__main__':
    logger.warn('started')

    main()
