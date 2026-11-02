import os
import asyncio
import json
import logging
from aiohttp import web
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO  # DEBUG/INFO level
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file")

logger.info(f"Bot token loaded: {TELEGRAM_TOKEN[:5]}...")

# Store connected SSE clients
connected_clients = set()

async def send_sse_message(message: dict):
    """Send message to all connected SSE clients"""
    data = json.dumps(message)
    logger.info(f"Broadcasting SSE message: {data}")
    dead_clients = set()
    
    for client in connected_clients:
        try:
            await client.send_str(f"data: {data}\n\n")
        except Exception as e:
            logger.error(f"Error sending to client: {e}")
            dead_clients.add(client)
    
    # Remove dead clients
    connected_clients.difference_update(dead_clients)

async def sse_handler(request):
    """Handle SSE connections"""
    logger.info("New SSE client connecting")
    response = web.Response(
        content_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'Access-Control-Allow-Origin': '*'
        }
    )
    
    await response.prepare(request)
    connected_clients.add(response)
    
    logger.info(f"SSE client connected. Total clients: {len(connected_clients)}")
    
    try:
        # Keep connection alive
        while True:
            await asyncio.sleep(30)
            await response.write(b"event: ping\ndata: ping\n\n")
    except ConnectionResetError:
        logger.info("SSE client disconnected")
    finally:
        connected_clients.discard(response)
        logger.info(f"SSE client removed. Remaining clients: {len(connected_clients)}")
    
    return response

async def process_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process incoming Telegram messages"""
    logger.debug("Entering process_telegram_message")
    
    if update.message is None:
        logger.warning("Received update with no message")
        return

    user_query = update.message.text
    chat_id = update.message.chat_id
    username = update.message.from_user.username or "Unknown"
    
    logger.info(f"Received message from {username} ({chat_id}): {user_query}")

    try:
        # Import the agent's main function
        from agent import main
        
        # Send acknowledgment to user
        await context.bot.send_message(
            chat_id=chat_id,
            text="Processing your query..."
        )
        
        # Broadcast that we're processing
        await send_sse_message({
            'type': 'processing',
            'query': user_query,
            'user': username
        })
        
        # Run the agent with the user's query
        logger.info(f"Starting agent processing for query: {user_query}")
        agent_response = await main(user_query)
        logger.info(f"Agent response received: {agent_response}")
        
        # Send the response back to Telegram
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"Response: {agent_response}"
        )
        
        # Send to SSE clients
        await send_sse_message({
            'type': 'response',
            'query': user_query,
            'response': agent_response,
            'user': username
        })
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        error_message = f"Error processing query: {str(e)}"
        await context.bot.send_message(
            chat_id=chat_id,
            text=error_message
        )
        await send_sse_message({
            'type': 'error',
            'query': user_query,
            'error': str(e),
            'user': username
        })

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    logger.debug("Entering start_command handler")
    
    if update.effective_chat is None:
        logger.error("No effective chat in start command")
        return
        
    username = update.message.from_user.username if update.message else "Unknown"
    logger.info(f"New user started bot: {username}")
    
    welcome_message = (
        "👋 Welcome! I'm ready to process your queries.\n"
        "Just send me a message and I'll process it through the agent.\n"
        "Your queries will be processed and responses will be sent here."
    )
    
    try:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=welcome_message
        )
        logger.info(f"Welcome message sent to {username}")
    except Exception as e:
        logger.error(f"Error sending welcome message: {e}", exc_info=True)

async def init_telegram_bot():
    """Initialize the Telegram bot"""
    logger.info("Initializing Telegram bot")
    
    try:
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler('start', start_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_telegram_message))
        
        # Start the bot
        await application.initialize()
        await application.start()
        
        # Start polling in the background
        async def start_polling():
            await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            logger.info("Telegram bot polling started")
            
        asyncio.create_task(start_polling())
        
        logger.info("Telegram bot initialized successfully")
        return application
    except Exception as e:
        logger.error(f"Failed to initialize Telegram bot: {e}", exc_info=True)
        raise

async def init_app():
    """Initialize the web application"""
    logger.info("Initializing web application")
    app = web.Application()
    app.router.add_get('/events', sse_handler)
    return app

async def main():
    """Main function to run both the SSE server and Telegram bot"""
    logger.info("Starting application")
    
    try:
        # Initialize both the web app and Telegram bot
        app = await init_app()
        telegram_bot = await init_telegram_bot()

        # Start the web server
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8080)
        
        await site.start()
        logger.info("SSE Server started at http://localhost:8080")
        
        # Keep the server running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in main loop: {e}", exc_info=True)
        raise
    finally:
        if 'runner' in locals():
            await runner.cleanup()
        if 'telegram_bot' in locals():
            await telegram_bot.stop()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application shutdown requested")
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True) 