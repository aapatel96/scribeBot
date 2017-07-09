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

next_keyboard = ReplyKeyboardMarkup([[KeyboardButton("next")]], resize_keyboard=True, one_time_keyboard=True)


start_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("start", callback_data='start')]])

start_keyboard2 = InlineKeyboardMarkup([[InlineKeyboardButton("beginning", callback_data='start'),InlineKeyboardButton("resume", callback_data='resume')]])

archive_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("archive", callback_data='archive'),InlineKeyboardButton("restart", callback_data='start')]])

resume_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("resume", callback_data='resume')]])

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


SETTITLEASKFIRSTSEG,ADDTERMORDONE,NEXT,STARTPOINT= range(4)

logger = logging.getLogger(__name__)
client = pymongo.MongoClient('mongodb://heroku_l5r7q33g:30htf2r3udd48vctqnnqal1f7h@ds153352.mlab.com:53352/heroku_l5r7q33g')

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
    user2add = userformat
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
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END


    mid = queryObj.message.message_id
    message=update.callback_query.message.text
    messageComponents=message.split('\n')
    noteidline = messageComponents[0]
    collid= noteidline[4:]
    intcollid = int(collid)

    if str(queryData) == 'start':
        collections.update({"id":intcollid,"user_id":user["id"]},{"$set":{"index":0}})
        collection = collections.find_one({"id":intcollid,"user_id":user["id"]})
        users.update({"id":user["id"]},{"$set":{"currentReadCollection":collection['id']}})
        queryObj.message.reply_text(collection['collection'][collection['index']])
        collections.update({"id":intcollid,"user_id":user["id"]},{"$inc":{"index":1}})
        collection = collections.find_one({"id":intcollid,"user_id":user["id"]})
        if collection['index']==len(collection['collection']):
            collections.update({"id":intcollid,"user_id":user["id"]},{"$set":{"index":0}})
            queryObj.message.reply_text("COLL"+str(collection['id'])+'\n'+'\n'+"You have reached the end of this reading",reply_markup=archive_keyboard)
            return ConversationHandler.END
        return NEXT

    if str(queryData) == 'resume':
        print "resume"
        collection = collections.find_one({"id":intcollid,"user_id":user["id"]})
        print collection
        if collection==None:
            queryObj.message.reply_text('collection not found')
            return ConversationHandler.END

        users.update({"id":user["id"]},{"$set":{"currentReadCollection":collection['id']}})
        queryObj.message.reply_text(collection['collection'][collection['index']],reply_markup=next_keyboard)
        collections.update({"id":intcollid,"user_id":user["id"]},{"$inc":{"index":1}})
        collection = collections.find_one({"id":intcollid,"user_id":user["id"]})
        print collection
        if collection['index']==len(collection['collection']):
            print "if branch"
            collections.update({"id":intcollid,"user_id":user["id"]},{"$set":{"index":0}})
            queryObj.message.reply_text("COLL"+str(collection['id'])+'\n'+'\n'+"You have reached the end of this reading",reply_markup=archive_keyboard)
            return ConversationHandler.END
        return NEXT
    
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
        return ConversationHandler.END



def askTitle(bot,update):
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END

    update.message.reply_text("Name?")
    return SETTITLEASKFIRSTSEG

def setTitleAskFirstSeg(bot,update):
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END

    users.update({"id":user['id']},{"$push":{"currentSetCollection":update.message.text}})
    update.message.reply_text("Alright, I am listening...")
    update.message.reply_text("Send /done when you are done")
    return ADDTERMORDONE


def addTerm(bot,update):
    try:        
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END


    users.update({"id":user['id']},{"$push":{"currentSetCollection":update.message.text}})
    return ADDTERMORDONE


def done(bot,update):
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END
    collection = collectionformat
    print collection

    collection_id = randint(10000,99999)
    while collection_id in user['collection_ids']:
        collection_id = randint(10000,99999)

    collection['id']= collection_id
    collection['user_id'] = update.message.chat.id
    collection['collection']= user['currentSetCollection'][1:]
    collection['title']= user['currentSetCollection'][0]
    collections.insert_one(collection)
    users.update({"id":update.message.chat.id},{"$set":{"currentSetCollection":[]}})
    users.update({"id":update.message.chat.id},{"$push":{"collection_ids":collection_id}})
    update.message.reply_text("Collection set!")
    return ConversationHandler.END


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

    return STARTPOINT

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
    return ConversationHandler.END

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
    collection_ids.append(collection_id)
    users.update({"id":user['id']},{"$set":{"collection_ids":collection_ids}})
    update.message.reply_text("Collection restored!")
    print collection['title']
    collection=collection.find_one({"id":collection_id,"user_id":user["id"]})
    update.message.reply_text("COLL"+str(collection_id)+'\n'+'\n'+collection['title'],reply_markup=start_keyboard)
    return ConversationHandler.END


def nextSeg(bot,update):
    try:
        user = users.find_one({"id":update.message.chat.id})
    except:
        update.message.reply_text("You are not registered. Press /start and then resend command2")
        return ConversationHandler.END
    
    if update.message.text=="next":
        print user['currentReadCollection']
        print update.message.chat.id
        collection = collections.find_one({"id":user['currentReadCollection'],"user_id":update.message.chat.id})
        if collection['index']==len(collection['collection']):
            collections.update({"id":user['currentReadCollection'],"user_id":user["id"]},{"$set":{"index":0}})
            update.message.reply_text("You have reached the end of this collection")
            update.message.reply_text("COLL"+str(collection['id']),reply_markup=archive_keyboard)
            return ConversationHandler.END
        print collection
        update.message.reply_text(collection['collection'][collection['index']],reply_markup=next_keyboard)
        collections.update({"id":user['currentReadCollection'],"user_id":update.message.chat.id},{"$inc":{"index":1}})
        return NEXT

    if update.message.text=="exit":
        users.update({"user_id":update.message.chat.id},{"$set":{"currentReadCollection":None}})
        update.message.reply_text("COLL"+str(collection['id'])+'\n'+'\n'+"You have exited this reading",reply_markup=resume_keyboard)
        return ConversationHandler.END

def main():
    # Create the EventHandler and pass it your bot's token.
    TOKEN = "439473644:AAHBJTxu6Um7_7cq9ltmYbLPqSNMI6tW688"
    updater = Updater(TOKEN)
    PORT = int(os.environ.get('PORT', '5000'))
    # job_q= updater.job_queue

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help))

    #dp.add_handler(CallbackQueryHandler(menuButtons))
    dp.add_handler(CommandHandler("collections",mycollections))
    dp.add_handler(RegexHandler("^/read",read))
    dp.add_handler(RegexHandler("^/archive",archivef))
    dp.add_handler(RegexHandler("^/restore",restore))





    createreadCollection = ConversationHandler(
    entry_points=[CommandHandler("new",askTitle),CallbackQueryHandler(menuButtons),RegexHandler("^/read",read)],
    states={

        STARTPOINT: [CallbackQueryHandler(menuButtons),
                      
                ],
        SETTITLEASKFIRSTSEG: [MessageHandler(Filters.text,
                                   setTitleAskFirstSeg)
                  ],
        NEXT: [MessageHandler(Filters.text,nextSeg)],
        
        ADDTERMORDONE: [MessageHandler(Filters.text,addTerm),
                        CommandHandler("done",done)                        
                ],


    },

    fallbacks=[RegexHandler('^cancel$', help)]
    )

    dp.add_handler(createreadCollection)
    # log all errors
    dp.add_error_handler(error)

    # Start the Bot

##    updater.start_polling()
    updater.start_webhook(listen="0.0.0.0",
                      port=PORT,
                      url_path=TOKEN)
    updater.bot.set_webhook("https://notetakingsbot.herokuapp.com/" + TOKEN)
    updater.idle()


if __name__ == '__main__':
    logger.warn('started')

    main()
