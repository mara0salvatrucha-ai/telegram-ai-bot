import asyncio
import json
import os
import sys
import base64
import ssl
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
from telethon import TelegramClient, events, Button
from telethon.errors import RPCError
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, InputPeerSelf

# ============ КОНФИГУРАЦИЯ ============
API_ID = int(os.environ.get('API_ID', '39678712'))
API_HASH = os.environ.get('API_HASH', '3089ac53d532e75deb5dd641e4863d49')
PHONE = os.environ.get('PHONE', '+919036205120')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8593923331:AAHJcTOz2-ePSUxApx_cSuzdye3W0aIomJE')

# OnlySQ API
AI_API_URL = 'https://api.onlysq.ru/ai/openai/chat/completions'
AI_API_KEY = os.environ.get('OPENAI_API_KEY', 'openai')
MODEL_NAME = 'gpt-5.2-chat'

# Файлы БД
DB_FILE = 'messages.json'
ACTIVE_CHATS_FILE = 'active_chats.json'
DELETED_MESSAGES_DB = 'deleted_messages.json'
SAVER_CONFIG_FILE = 'saver_config.json'
MESSAGES_STORAGE_DB = 'messages_storage.json'
ANIMATION_CONFIG_FILE = 'animation_config.json'
MUTE_CONFIG_FILE = 'mute_config.json'
TEMP_SELECTION_FILE = 'temp_selection.json'
AI_CONFIG_FILE = 'ai_config.json'
MUTED_USERS_DB = 'muted_users_db.json'
ABOUT_CONFIG_FILE = 'about_config.json'

SESSION_NAME = 'railway_session'
MEDIA_FOLDER = 'saved_media'
OWNER_ID = None
BOT_ID = None

last_command_message = {}
COMMAND_PREFIXES = ['.saver', '.deleted', '.aiconfig', '.aistop', '.aiclear', '.anim', '.замолчи', '.говори', '.del', '.список', '.neiro', '.bio']

# Глобальное состояние
user_selection_state = {}
last_menu_msg = {}
bio_state = {}

# ============ UNICODE ШРИФТЫ ============
FONTS = {
    'bold': lambda t: "".join([chr(0x1D400 + ord(c) - 65) if 65 <= ord(c) <= 90 else chr(0x1D41A + ord(c) - 97) if 97 <= ord(c) <= 122 else c for c in t]),
    'italic': lambda t: "".join([chr(0x1D434 + ord(c) - 65) if 65 <= ord(c) <= 90 else chr(0x1D44E + ord(c) - 97) if 97 <= ord(c) <= 122 else c for c in t]),
    'bolditalic': lambda t: "".join([chr(0x1D468 + ord(c) - 65) if 65 <= ord(c) <= 90 else chr(0x1D482 + ord(c) - 97) if 97 <= ord(c) <= 122 else c for c in t]),
    'script': lambda t: "".join([chr(0x1D49C + ord(c) - 65) if 65 <= ord(c) <= 90 else chr(0x1D4B6 + ord(c) - 97) if 97 <= ord(c) <= 122 else c for c in t]),
    'fraktur': lambda t: "".join([chr(0x1D504 + ord(c) - 65) if 65 <= ord(c) <= 90 else chr(0x1D51E + ord(c) - 97) if 97 <= ord(c) <= 122 else c for c in t]),
    'smallcaps': lambda t: t.lower().replace('а','ᴀ').replace('б','ʙ').replace('в','ᴠ').replace('г','ɢ').replace('д','ᴅ').replace('е','ᴇ').replace('ж','ᴊ').replace('з','ᴢ').replace('и','ɪ').replace('й','ɪ̆').replace('к','ᴋ').replace('л','ʟ').replace('м','ᴍ').replace('н','ɴ').replace('о','ᴏ').replace('п','ᴘ').replace('р','ᴩ').replace('с','ᴄ').replace('т','ᴛ').replace('у','ʏ').replace('ф','ғ').replace('х','х').replace('ц','ᴄ').replace('ч','ᴄ').replace('ш','ш').replace('щ','щ').replace('ъ','ъ').replace('ы','ы').replace('ь','ь').replace('э','ɛ').replace('ю','ю').replace('я','я')
}

# ============ ФУНКЦИИ БД ============
def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_db(data):
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_ai_config():
    """Загрузка конфигурации ИИ"""
    if os.path.exists(AI_CONFIG_FILE):
        try:
            with open(AI_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if 'advanced' not in config:
                    advanced = {}
                    for key in ['lowercase', 'auto_reply_all', 'voice_enabled', 'photo_enabled', 'max_history', 'temperature']:
                        if key in config:
                            advanced[key] = config.pop(key)
                    if advanced:
                        config['advanced'] = advanced
                return config
        except:
            pass
    return {
        'enabled': False,
        'personality': 'отвечай как обычный человек, кратко и по делу. пиши с маленькой буквы'
    }

def save_ai_config(config):
    try:
        with open(AI_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_muted_users_db():
    if os.path.exists(MUTED_USERS_DB):
        try:
            with open(MUTED_USERS_DB, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_muted_users_db(data):
    try:
        with open(MUTED_USERS_DB, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def mute_user_new(user_id, user_name, chat_id):
    db = load_muted_users_db()
    user_key = str(user_id)
    db[user_key] = {
        'user_name': user_name,
        'muted_at': datetime.now().isoformat(),
        'chat_id': chat_id
    }
    save_muted_users_db(db)

def unmute_user_new(user_id):
    db = load_muted_users_db()
    user_key = str(user_id)
    if user_key in db:
        user_info = db.pop(user_key)
        save_muted_users_db(db)
        return user_info
    return None

def is_user_muted_new(user_id):
    db = load_muted_users_db()
    return str(user_id) in db

def get_all_muted_users():
    db = load_muted_users_db()
    return db

def load_about_config():
    if os.path.exists(ABOUT_CONFIG_FILE):
        try:
            with open(ABOUT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Обратная совместимость - добавляем audio_position если нет
                if 'audio_position' not in config:
                    config['audio_position'] = 'after'
                return config
        except:
            pass
    return {
        'enabled': False,
        'text': '👋 Привет! Я сейчас занят, отвечу позже.',
        'media_path': None,
        'audio_path': None,
        'audio_position': 'after',
        'seen_users': []
    }

def save_about_config(config):
    try:
        with open(ABOUT_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_animation_config():
    if os.path.exists(ANIMATION_CONFIG_FILE):
        try:
            with open(ANIMATION_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_animation_config(config):
    try:
        with open(ANIMATION_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except:
        pass

def get_animation_settings(chat_id):
    config = load_animation_config()
    chat_key = str(chat_id)
    if chat_key in config:
        settings = config[chat_key]
        return {
            'mode': settings.get('mode'),
            'font': settings.get('font'),
            'duration': settings.get('duration', 40),
            'interval': settings.get('interval', 0.5)
        }
    return {'mode': None, 'font': None, 'duration': 40, 'interval': 0.5}

def set_animation_mode(chat_id, mode, font=None):
    config = load_animation_config()
    chat_key = str(chat_id)
    if chat_key not in config:
        config[chat_key] = {'duration': 40, 'interval': 0.5}
    config[chat_key]['mode'] = mode
    if font is not None:
        config[chat_key]['font'] = font
    save_animation_config(config)

def load_mute_config():
    if os.path.exists(MUTE_CONFIG_FILE):
        try:
            with open(MUTE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_mute_config(config):
    try:
        with open(MUTE_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except:
        pass

def mute_user(chat_id, user_id, user_name):
    config = load_mute_config()
    chat_key = str(chat_id)
    if chat_key not in config:
        config[chat_key] = {}
    config[chat_key][str(user_id)] = {
        'user_name': user_name,
        'muted_at': datetime.now().isoformat()
    }
    save_mute_config(config)

def unmute_user(chat_id, user_id):
    config = load_mute_config()
    chat_key = str(chat_id)
    if chat_key in config and str(user_id) in config[chat_key]:
        user_info = config[chat_key].pop(str(user_id))
        save_mute_config(config)
        return user_info
    return None

def is_user_muted(chat_id, user_id):
    config = load_mute_config()
    chat_key = str(chat_id)
    return chat_key in config and str(user_id) in config[chat_key]

def get_muted_users(chat_id):
    config = load_mute_config()
    chat_key = str(chat_id)
    return config.get(chat_key, {})

# ============ АНИМАЦИОННЫЕ ФУНКЦИИ ============
async def animate_rainbow(message_obj, text, duration=40, interval=0.5):
    frames_count = int(duration / interval)
    colors = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤']
    for frame in range(frames_count):
        color_bar = ''.join([colors[(i+frame)%len(colors)] for i in range(len(colors))])
        progress = int((frame / frames_count) * 10)
        bar = '▰' * progress + '▱' * (10 - progress)
        try:
            await message_obj.edit(f'{color_bar}\n{text}\n{bar}')
            await asyncio.sleep(interval)
        except:
            break
    try:
        await message_obj.edit(f'🌈 {text}')
    except:
        pass

async def animate_caps(message_obj, text, duration=40, interval=0.5):
    frames_count = int(duration / interval)
    try:
        await message_obj.edit(text)
        await asyncio.sleep(interval)
    except:
        pass
    
    for frame in range(1, frames_count - 1):
        if frame % 2 == 1:
            new_text = ''.join([c.upper() if i % 2 == 1 else c.lower() for i, c in enumerate(text)])
        else:
            new_text = ''.join([c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(text)])
        try:
            await message_obj.edit(new_text)
            await asyncio.sleep(interval)
        except:
            break
    
    try:
        await message_obj.edit(text)
    except:
        pass

async def run_animation(message_obj, text, anim_type, duration=40, interval=0.5, font=None):
    # Применяем шрифт если указан
    if font and font in FONTS:
        text = FONTS[font](text)
    
    animations = {
        'rainbow': animate_rainbow,
        'caps': animate_caps
    }
    if anim_type in animations:
        await animations[anim_type](message_obj, text, duration, interval)

# ============ ОСТАЛЬНЫЕ БАЗОВЫЕ ФУНКЦИИ ============
def load_active_chats():
    if os.path.exists(ACTIVE_CHATS_FILE):
        try:
            with open(ACTIVE_CHATS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_active_chats(data):
    try:
        with open(ACTIVE_CHATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def is_chat_active(chat_id):
    return str(chat_id) in load_active_chats() and load_active_chats()[str(chat_id)]

def activate_chat(chat_id):
    chats = load_active_chats()
    chats[str(chat_id)] = True
    save_active_chats(chats)

def deactivate_chat(chat_id):
    chats = load_active_chats()
    chats[str(chat_id)] = False
    save_active_chats(chats)

def load_messages_storage():
    if os.path.exists(MESSAGES_STORAGE_DB):
        try:
            with open(MESSAGES_STORAGE_DB, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_messages_storage(data):
    try:
        with open(MESSAGES_STORAGE_DB, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def store_message_immediately(chat_id, message_data):
    storage = load_messages_storage()
    chat_key = str(chat_id)
    if chat_key not in storage:
        storage[chat_key] = []
    storage[chat_key].append(message_data)
    if len(storage[chat_key]) > 1000:
        storage[chat_key] = storage[chat_key][-1000:]
    save_messages_storage(storage)
    return True

def get_stored_message(chat_id, message_id):
    storage = load_messages_storage()
    if chat_id:
        chat_key = str(chat_id)
        if chat_key in storage:
            for msg in storage[chat_key]:
                if msg.get('message_id') == message_id:
                    return msg
    for chat_key, messages in storage.items():
        for msg in messages:
            if msg.get('message_id') == message_id:
                return msg
    return None

def is_command_message(text):
    if not text:
        return False
    text_lower = text.lower().strip()
    return any(text_lower.startswith(prefix.lower()) for prefix in COMMAND_PREFIXES)

def load_deleted_messages_db():
    if os.path.exists(DELETED_MESSAGES_DB):
        try:
            with open(DELETED_MESSAGES_DB, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_deleted_messages_db(data):
    try:
        with open(DELETED_MESSAGES_DB, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def load_saver_config():
    if os.path.exists(SAVER_CONFIG_FILE):
        try:
            with open(SAVER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                if 'save_text' not in config:
                    config['save_text'] = True
                if 'save_voice' not in config:
                    config['save_voice'] = True
                if 'save_ttl_media' not in config:
                    config['save_ttl_media'] = False
                if 'save_bots' not in config:
                    config['save_bots'] = False
                return config
        except:
            pass
    return {
        'save_private': False,
        'save_groups': False,
        'save_channels': [],
        'save_media': True,
        'save_ttl': True,
        'save_text': True,
        'save_voice': True,
        'save_ttl_media': False,
        'save_bots': False
    }

def save_saver_config(config):
    try:
        with open(SAVER_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except:
        pass

def should_save_message(chat_id, is_private, is_group):
    config = load_saver_config()
    chat_id_str = str(chat_id)
    
    if chat_id_str in config['save_channels']:
        return True
    
    if is_private and config['save_private']:
        return True
        
    if is_group and config['save_groups']:
        return True

    return False

def add_deleted_message(chat_id, message_data):
    if is_command_message(message_data.get('text', '')):
        return
    
    config = load_saver_config()
    
    if not config.get('save_text', True):
        if not (message_data.get('has_photo') or message_data.get('has_video') or 
                message_data.get('has_document') or message_data.get('has_voice')):
            return
    
    if not config.get('save_media', True) and message_data.get('has_photo'):
        return
    
    if not config.get('save_media', True) and message_data.get('has_video'):
        return
    
    if not config.get('save_media', True) and message_data.get('has_document'):
        return
    
    if not config.get('save_voice', True) and message_data.get('has_voice'):
        return
    
    db = load_deleted_messages_db()
    chat_key = str(chat_id)
    if chat_key not in db:
        db[chat_key] = []
    db[chat_key].append(message_data)
    if len(db[chat_key]) > 1000:
        db[chat_key] = db[chat_key][-1000:]
    save_deleted_messages_db(db)

def get_all_senders_with_deleted():
    db = load_deleted_messages_db()
    sender_stats = {}
    
    for chat_key, messages in db.items():
        for msg in messages:
            sender_id = msg.get('sender_id')
            if sender_id is None or sender_id == OWNER_ID:
                continue
            sender_name = msg.get('sender_name', 'Неизвестно')
            if sender_id not in sender_stats:
                sender_stats[sender_id] = {'name': sender_name, 'count': 0}
            sender_stats[sender_id]['count'] += 1
    
    sorted_senders = sorted(sender_stats.items(), key=lambda x: x[1]['count'], reverse=True)
    return [(sid, data['name'], data['count']) for sid, data in sorted_senders]

def get_deleted_messages(chat_id=None, limit=None, sender_id=None, message_type=None):
    db = load_deleted_messages_db()
    messages = []
    
    chat_keys = [str(chat_id)] if chat_id is not None else db.keys()
    
    for ck in chat_keys:
        if ck not in db:
            continue
        for msg in db[ck]:
            if is_command_message(msg.get('text', '')):
                continue
            if sender_id is not None and msg.get('sender_id') != sender_id:
                continue
                
            if message_type == 'photo' and not msg.get('has_photo'):
                continue
            if message_type == 'video' and not msg.get('has_video'):
                continue
            if message_type == 'document' and not msg.get('has_document'):
                continue
            if message_type == 'voice' and not msg.get('has_voice'):
                continue
            if message_type == 'text' and (msg.get('has_photo') or msg.get('has_video') or 
                                          msg.get('has_document') or msg.get('has_voice')):
                continue
                
            messages.append(msg)
    
    messages.sort(key=lambda x: x.get('deleted_at', ''), reverse=True)
    if limit:
        messages = messages[:limit]
    return messages

def clear_deleted_messages_by_type(chat_id, message_type, target_chat_id=None, sender_id=None):
    db = load_deleted_messages_db()
    
    if message_type == 'all_global':
        db.clear()
        save_deleted_messages_db(db)
        return True
    
    if sender_id is not None:
        for chat_key in db:
            db[chat_key] = [m for m in db[chat_key] if m.get('sender_id') != sender_id]
        save_deleted_messages_db(db)
        return True
    
    target = str(target_chat_id) if target_chat_id is not None else str(chat_id)
    
    if target not in db:
        return False
    
    messages = db[target]
    
    if message_type == 'all':
        db[target] = []
    elif message_type == 'photo':
        db[target] = [m for m in messages if not m.get('has_photo')]
    elif message_type == 'video':
        db[target] = [m for m in messages if not m.get('has_video')]
    elif message_type == 'document':
        db[target] = [m for m in messages if not m.get('has_document')]
    elif message_type == 'voice':
        db[target] = [m for m in messages if not m.get('has_voice')]
    elif message_type == 'text':
        db[target] = [m for m in messages if (m.get('has_photo') or m.get('has_video') or 
                                              m.get('has_document') or m.get('has_voice'))]
    
    save_deleted_messages_db(db)
    return True

def save_temp_selection(chat_id, users_list):
    chat_key = str(chat_id)
    if chat_key not in user_selection_state:
        user_selection_state[chat_key] = {}
    user_selection_state[chat_key]['users'] = users_list
    user_selection_state[chat_key]['timestamp'] = datetime.now()

def load_temp_selection(chat_id):
    chat_key = str(chat_id)
    if chat_key not in user_selection_state:
        return None
    data = user_selection_state[chat_key]
    if datetime.now() > data['timestamp'] + timedelta(minutes=5):
        del user_selection_state[chat_key]
        return None
    return data['users']

async def save_media_file(message, media_folder=MEDIA_FOLDER):
    try:
        Path(media_folder).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        chat_id, msg_id = message.chat_id, message.id
        
        if message.photo:
            ext, mtype = 'jpg', 'photo'
        elif message.video:
            if hasattr(message.media, 'video_note') or (hasattr(message, 'video_note') and message.video_note):
                ext, mtype = 'mp4', 'videonote'
            else:
                ext, mtype = 'mp4', 'video'
        elif message.voice:
            ext, mtype = 'ogg', 'voice'
        elif message.audio:
            ext, mtype = 'mp3', 'audio'
        elif message.document:
            ext = 'bin'
            if hasattr(message.document, 'attributes'):
                for attr in message.document.attributes:
                    if hasattr(attr, 'file_name') and '.' in attr.file_name:
                        ext = attr.file_name.split('.')[-1]
                        break
            mtype = 'document'
        else:
            return None
            
        filename = f'{mtype}_{chat_id}_{msg_id}_{timestamp}.{ext}'
        filepath = os.path.join(media_folder, filename)
        await message.download_media(filepath)
        print(f'💾 Сохранен: {filename}')
        return filepath
    except Exception as e:
        print(f'⚠️ Ошибка сохранения медиа: {e}')
        import traceback
        traceback.print_exc()
        return None

db = load_db()

if os.path.exists(TEMP_SELECTION_FILE):
    try:
        with open(TEMP_SELECTION_FILE, 'r', encoding='utf-8') as f:
            loaded_state = json.load(f)
            for k, v in loaded_state.items():
                if 'timestamp' in v and isinstance(v['timestamp'], str):
                    try:
                        v['timestamp'] = datetime.fromisoformat(v['timestamp'])
                    except:
                        v['timestamp'] = datetime.now()
            user_selection_state = loaded_state
    except:
        user_selection_state = {}
else:
    user_selection_state = {}

# ============ ФУНКЦИИ ИИ С ONLYSQ ============
async def transcribe_voice(voice_path):
    """Транскрибация голосового/видеосообщения через API (Audio Transcriptions)"""
    try:
        if not os.path.exists(voice_path):
            return "[файл не найден]"

        base_url = AI_API_URL.replace('/chat/completions', '')
        transcribe_url = f"{base_url}/audio/transcriptions"

        content_type = 'audio/ogg'
        if voice_path.lower().endswith('.mp4'):
            content_type = 'audio/mp4'
        elif voice_path.lower().endswith('.mp3'):
            content_type = 'audio/mpeg'
        elif voice_path.lower().endswith('.wav'):
            content_type = 'audio/wav'

        data = aiohttp.FormData()
        data.add_field('file',
                       open(voice_path, 'rb'),
                       filename=os.path.basename(voice_path),
                       content_type=content_type)
        data.add_field('model', 'whisper-1')

        headers = {
            'Authorization': f'Bearer {AI_API_KEY}'
        }

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            async with session.post(transcribe_url, data=data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    return result.get('text', '[не удалось распознать]')
                else:
                    error_text = await resp.text()
                    print(f'❌ Ошибка транскрипции ({resp.status}): {error_text}')
                    return f"[ошибка транскрипции: {resp.status}]"
    except Exception as e:
        print(f'❌ Ошибка транскрипции: {e}')
        return f"[ошибка: {str(e)}]"

async def describe_photo(photo_path):
    """Описание фото через OnlySQ Vision API"""
    try:
        config = load_ai_config()
        
        with open(photo_path, 'rb') as f:
            photo_data = base64.b64encode(f.read()).decode('utf-8')
        
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=120)) as session:
            payload = {
                'model': 'gpt-5.2-chat',
                'messages': [
                    {
                        'role': 'user',
                        'content': [
                            {
                                'type': 'text',
                                'text': 'опиши что на фото кратко, одним предложением'
                            },
                            {
                                'type': 'image_url',
                                'image_url': {
                                    'url': f'data:image/jpeg;base64,{photo_data}'
                                }
                            }
                        ]
                    }
                ],
                'temperature': 0.7
            }
            
            headers = {
                'Authorization': f'Bearer {AI_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            async with session.post(AI_API_URL, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                    return content or "[фотография]"
                else:
                    error_text = await resp.text()
                    print(f'❌ Vision API ошибка {resp.status}: {error_text}')
                    return f"[ошибка анализа фото: {resp.status}]"
    except Exception as e:
        print(f'❌ Ошибка описания фото: {e}')
        import traceback
        traceback.print_exc()
        return f"[ошибка: {str(e)}]"

async def get_ai_response(messages, config=None):
    """Получение ответа от ИИ через OnlySQ API"""
    try:
        if config is None:
            config = load_ai_config()
        
        system_prompt = config.get('personality', 'отвечай как обычный человек, кратко и по делу. пиши с маленькой буквы')
        
        advanced = config.get('advanced', {})
        temperature = advanced.get('temperature', 0.7)
        lowercase = advanced.get('lowercase', True)
        
        api_messages = [{'role': 'system', 'content': system_prompt}]
        api_messages.extend(messages)
        
        connector = aiohttp.TCPConnector(ssl=False)
        
        async with aiohttp.ClientSession(connector=connector, timeout=aiohttp.ClientTimeout(total=60)) as session:
            payload = {
                'model': MODEL_NAME,
                'messages': api_messages,
                'temperature': temperature
            }
            
            headers = {
                'Authorization': f'Bearer {AI_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            async with session.post(AI_API_URL, json=payload, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    content = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
                    
                    if not content:
                        return 'хз'
                    
                    if lowercase and content:
                        if content[0].isupper():
                            content = content[0].lower() + content[1:]
                    
                    return content
                else:
                    error_text = await resp.text()
                    print(f'❌ OnlySQ API ошибка {resp.status}: {error_text}')
                    return 'не смог ответить'
    except Exception as e:
        print(f'❌ OnlySQ API ошибка: {e}')
        import traceback
        traceback.print_exc()
        return 'ошибка апи'

def get_chat_history(chat_id, limit=10):
    """Получить историю чата"""
    config = load_ai_config()
    advanced = config.get('advanced', {})
    max_history = advanced.get('max_history', 20)
    limit = min(limit, max_history)
    
    chat_key = str(chat_id)
    if chat_key not in db:
        db[chat_key] = []
    
    filtered = [msg for msg in db[chat_key] if not (msg.get('role') == 'assistant' and 'ошибка' in msg.get('content', '').lower())]
    return filtered[-limit:]

def save_message(chat_id, role, content):
    """Сохранить сообщение в историю"""
    chat_key = str(chat_id)
    if chat_key not in db:
        db[chat_key] = []
    
    if role == 'assistant' and 'ошибка' in content.lower():
        return
    
    message = {'role': role, 'content': content}
    db[chat_key].append(message)
    
    config = load_ai_config()
    advanced = config.get('advanced', {})
    max_history = advanced.get('max_history', 20)
    
    if len(db[chat_key]) > max_history * 2:
        db[chat_key] = db[chat_key][-max_history * 2:]
    
    save_db(db)

def clear_chat_history(chat_id):
    """Очистить историю чата"""
    chat_key = str(chat_id)
    if chat_key in db:
        db[chat_key] = []
        save_db(db)

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
bot = TelegramClient('bot_session', API_ID, API_HASH)

F_BOLD = lambda t: "".join([chr(0x1D400 + ord(c) - 65) if 65 <= ord(c) <= 90 else chr(0x1D41A + ord(c) - 97) if 97 <= ord(c) <= 122 else c for c in t])
F_MONO = lambda t: f"`{t}`"

# ============ ЛОГИКА КОНТРОЛЛЕРА (БОТА) ============
async def show_main_menu(event):
    buttons = [
        [Button.inline('🤖 𝐀𝐈 𝐒𝐞𝐭𝐭𝐢𝐧𝐠𝐬', b'menu_ai'), Button.inline('💾 𝐒𝐚𝐯𝐞𝐫', b'menu_saver')],
        [Button.inline('🎬 𝐀𝐧𝐢𝐦𝐚𝐭𝐢𝐨𝐧𝐬', b'menu_anim'), Button.inline('🔇 𝐌𝐮𝐭𝐞 𝐌𝐠𝐫', b'menu_mute')],
        [Button.inline('👋 𝐁𝐢𝐨 / 𝐀𝐮𝐭𝐨-𝐑𝐞𝐩𝐥𝐲', b'menu_about')],
        [Button.inline('📊 𝐒𝐲𝐬𝐭𝐞𝐦 𝐒𝐭𝐚𝐭𝐮𝐬', b'sys_status')]
    ]
    
    text = f"🎮 **𝐂𝐎𝐍𝐓𝐑𝐎𝐋 𝐏𝐀𝐍𝐄𝐋**\n\n🛡️ **𝐔𝐬𝐞𝐫:** {OWNER_ID}\n🤖 **𝐁𝐨𝐭:** @{(await bot.get_me()).username}\n\n👇 𝐒𝐞𝐥𝐞𝐜𝐭 𝐂𝐚𝐭𝐞𝐠𝐨𝐫𝐲:"
    
    if hasattr(event, 'data') and event.data:
        await event.edit(text, buttons=buttons)
        return None
    else:
        return await event.respond(text, buttons=buttons)

async def show_ai_menu(event):
    config = load_ai_config()
    adv = config.get('advanced', {})
    
    status = "✅ 𝐎𝐍" if config.get('enabled') else "❌ 𝐎𝐅𝐅"
    
    sched = config.get('schedule', {'start': 0, 'end': 0})
    sched_str = "🚫"
    if sched['start'] != sched['end']:
        sched_str = f"{sched['start']:02d}:00 - {sched['end']:02d}:00"

    buttons = [
        [Button.inline(f'⚡ 𝐌𝐚𝐬𝐭𝐞𝐫 𝐒𝐰𝐢𝐭𝐜𝐡: {status}', b'ai_toggle_main')],
        [Button.inline(f'🎤 𝐕𝐨𝐢𝐜𝐞: {"✅" if adv.get("voice_enabled", True) else "❌"}', b'ai_toggle_voice'),
         Button.inline(f'📷 𝐏𝐡𝐨𝐭𝐨: {"✅" if adv.get("photo_enabled", True) else "❌"}', b'ai_toggle_photo')],
        [Button.inline(f'🔄 𝐀𝐮𝐭𝐨-𝐑𝐞𝐩𝐥𝐲 𝐀𝐥𝐥: {"✅" if adv.get("auto_reply_all", False) else "❌"}', b'ai_toggle_auto')],
        [Button.inline(f'🔡 𝐋𝐨𝐰𝐞𝐫𝐜𝐚𝐬𝐞: {"✅" if adv.get("lowercase", True) else "❌"}', b'ai_toggle_lower')],
        [Button.inline(f'🔒 𝐏𝐫𝐢𝐯𝐚𝐭𝐞: {"✅" if config.get("ai_private_enabled", False) else "❌"}', b'ai_toggle_priv'),
         Button.inline(f'👥 𝐆𝐫𝐨𝐮𝐩𝐬: {"✅" if config.get("ai_groups_enabled", False) else "❌"}', b'ai_toggle_grp')],
        [Button.inline(f'🕒 𝐒𝐜𝐡𝐞𝐝𝐮𝐥𝐞: {sched_str}', b'ai_sched_info')],
        [Button.inline(f'🌡️ 𝐓𝐞𝐦𝐩: {adv.get("temperature", 0.7)}', b'ai_temp_info'),
         Button.inline(f'📊 𝐇𝐢𝐬𝐭𝐨𝐫𝐲: {adv.get("max_history", 20)}', b'ai_hist_info')],
        [Button.inline('🔙 𝐁𝐚𝐜𝐤', b'main_menu')]
    ]
    await event.edit(f"🤖 **𝐀𝐈 𝐂𝐎𝐍𝐅𝐈𝐆𝐔𝐑𝐀𝐓𝐈𝐎𝐍**\n\n🧠 **𝐌𝐨𝐝𝐞𝐥:** `{MODEL_NAME}`", buttons=buttons)

async def show_saver_menu(event):
    config = load_saver_config()
    buttons = [
        [Button.inline(f'📝 𝐓𝐞𝐱𝐭: {"✅" if config.get("save_text", True) else "❌"}', b'svr_text'),
         Button.inline(f'🖼️ 𝐌𝐞𝐝𝐢𝐚: {"✅" if config.get("save_media", True) else "❌"}', b'svr_media')],
        [Button.inline(f'🎤 𝐕𝐨𝐢𝐜𝐞: {"✅" if config.get("save_voice", True) else "❌"}', b'svr_voice'),
         Button.inline(f'⏱️ 𝐓𝐓𝐋: {"✅" if config.get("save_ttl_media", False) else "❌"}', b'svr_ttl')],
        [Button.inline(f'🤖 𝐁𝐨𝐭𝐬: {"✅" if config.get("save_bots", False) else "❌"}', b'svr_bots')],
        [Button.inline(f'🔓 𝐏𝐫𝐢𝐯𝐚𝐭𝐞: {"✅" if config.get("save_private", False) else "❌"}', b'svr_priv'),
         Button.inline(f'👥 𝐆𝐫𝐨𝐮𝐩𝐬: {"✅" if config.get("save_groups", False) else "❌"}', b'svr_grp')],
        [Button.inline('🗑️ 𝐂𝐥𝐞𝐚𝐫 𝐀𝐥𝐥', b'svr_clear_all')],
        [Button.inline('🗑️ 𝐓𝐞𝐱𝐭', b'svr_clear_text'), Button.inline('🗑️ 𝐏𝐡𝐨𝐭𝐨', b'svr_clear_photo')],
        [Button.inline('🗑️ 𝐕𝐢𝐝𝐞𝐨', b'svr_clear_video'), Button.inline('🗑️ 𝐕𝐨𝐢𝐜𝐞', b'svr_clear_voice')],
        [Button.inline('📉 𝐁𝐫𝐨𝐰𝐬𝐞 𝐃𝐞𝐥𝐞𝐭𝐞𝐝', b'svr_browse')],
        [Button.inline('🔙 𝐁𝐚𝐜𝐤', b'main_menu')]
    ]
    await event.edit("💾 **𝐒𝐀𝐕𝐄𝐑 𝐒𝐄𝐓𝐓𝐈𝐍𝐆𝐒**\n\nConfigure what deleted messages to save.", buttons=buttons)

async def show_saver_browser(event, page=0):
    senders = get_all_senders_with_deleted()
    if not senders:
        await event.edit("📭 **𝐍𝐨 𝐃𝐚𝐭𝐚**\nNo deleted messages found.", buttons=[[Button.inline('🔙 𝐁𝐚𝐜𝐤', b'menu_saver')]])
        return

    ITEMS_PER_PAGE = 5
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    current_page_items = senders[start:end]
    
    buttons = []
    for sid, name, count in current_page_items:
        buttons.append([Button.inline(f"👤 {name} ({count})", f'svr_view_{sid}'.encode())])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(Button.inline('⬅️', f'svr_page_{page-1}'.encode()))
    if end < len(senders):
        nav_buttons.append(Button.inline('➡️', f'svr_page_{page+1}'.encode()))
    
    if nav_buttons:
        buttons.append(nav_buttons)
    buttons.append([Button.inline('🔙 𝐁𝐚𝐜𝐤', b'menu_saver')])
    
    await event.edit(f"📉 **𝐃𝐄𝐋𝐄𝐓𝐄𝐃 𝐌𝐄𝐒𝐒𝐀𝐆𝐄𝐒**\nSelect a user to view:", buttons=buttons)

async def show_deleted_for_user(event, user_id, page=0):
    msgs = get_deleted_messages(sender_id=user_id)
    if not msgs:
        await event.edit("📭 Empty", buttons=[[Button.inline('🔙 Back', b'svr_browse')]])
        return
        
    ITEMS_PER_PAGE = 1
    start = page * ITEMS_PER_PAGE
    if start >= len(msgs):
        start = 0
    msg = msgs[start]
    
    text_type = "📝 𝐓𝐞𝐱𝐭"
    if msg.get('has_photo'):
        text_type = "🖼️ 𝐏𝐡𝐨𝐭𝐨"
    elif msg.get('has_video'):
        text_type = "🎥 𝐕𝐢𝐝𝐞𝐨"
    elif msg.get('has_voice'):
        text_type = "🎤 𝐕𝐨𝐢𝐜𝐞"
    
    content = f"🗑️ **𝐃𝐄𝐋𝐄𝐓𝐄𝐃 𝐌𝐒𝐆** ({start+1}/{len(msgs)})\n"
    content += f"👤 **𝐔𝐬𝐞𝐫:** {msg.get('sender_name')}\n"
    content += f"🕒 **𝐓𝐢𝐦𝐞:** {msg.get('deleted_at', '')[:16]}\n"
    content += f"🏷️ **𝐓𝐲𝐩𝐞:** {text_type}\n"
    content += f"💬 **𝐂𝐨𝐧𝐭𝐞𝐧𝐭:**\n`{msg.get('text', '')}`"
    
    buttons = []
    nav = []
    if page > 0:
        nav.append(Button.inline('⬅️', f'svr_u_{user_id}_{page-1}'.encode()))
    if start + 1 < len(msgs):
        nav.append(Button.inline('➡️', f'svr_u_{user_id}_{page+1}'.encode()))
    if nav:
        buttons.append(nav)
    buttons.append([Button.inline('🔙 𝐁𝐚𝐜𝐤', b'svr_browse')])
    
    await event.edit(content, buttons=buttons)

async def show_anim_menu(event):
    settings = get_animation_settings(event.chat_id)
    mode = settings['mode']
    font = settings['font']
    
    mode_text = "❌ 𝐎𝐅𝐅"
    if mode == 'rainbow':
        mode_text = "🌈 𝐑𝐚𝐢𝐧𝐛𝐨𝐰"
    elif mode == 'caps':
        mode_text = "🔤 𝐂𝐚𝐩𝐬"
    
    font_text = font if font else "𝐍𝐨𝐧𝐞"
    
    buttons = [
        [Button.inline(f'🌈 𝐑𝐚𝐢𝐧𝐛𝐨𝐰: {"✅" if mode=="rainbow" else "❌"}', b'anim_rainbow'),
         Button.inline(f'🔤 𝐂𝐚𝐩𝐬: {"✅" if mode=="caps" else "❌"}', b'anim_caps')],
        [Button.inline(f'🔤 𝐅𝐨𝐧𝐭: {font_text}', b'anim_font_menu')],
        [Button.inline(f'➖', b'anim_dur_minus'), Button.inline(f'⏱️ 𝐃𝐮𝐫: {settings["duration"]}s', b'noop'), Button.inline(f'➕', b'anim_dur_plus')],
        [Button.inline(f'➖', b'anim_int_minus'), Button.inline(f'⏲️ 𝐈𝐧𝐭: {settings["interval"]}s', b'noop'), Button.inline(f'➕', b'anim_int_plus')],
        [Button.inline('🔙 𝐁𝐚𝐜𝐤', b'main_menu')]
    ]
    await event.edit(f"🎬 **𝐀𝐍𝐈𝐌𝐀𝐓𝐈𝐎𝐍 𝐒𝐄𝐓𝐓𝐈𝐍𝐆𝐒**\n\n**Mode:** {mode_text}", buttons=buttons)

async def show_font_menu(event):
    buttons = [
        [Button.inline('𝐁𝐨𝐥𝐝', b'font_bold'), Button.inline('𝘐𝘵𝘢𝘭𝘪𝘤', b'font_italic')],
        [Button.inline('𝑩𝒐𝒍𝒅 𝑰𝒕𝒂𝒍𝒊𝒄', b'font_bolditalic'), Button.inline('𝒮𝒸𝓇𝒾𝓅𝓉', b'font_script')],
        [Button.inline('𝔉𝔯𝔞𝔨𝔱𝔲𝔯', b'font_fraktur'), Button.inline('ꜱᴍᴀʟʟᴄᴀᴘꜱ', b'font_smallcaps')],
        [Button.inline('❌ 𝐍𝐨 𝐅𝐨𝐧𝐭', b'font_none')],
        [Button.inline('🔙 𝐁𝐚𝐜𝐤', b'menu_anim')]
    ]
    await event.edit("🔤 **𝐒𝐄𝐋𝐄𝐂𝐓 𝐅𝐎𝐍𝐓**\n\nChoose animation font:", buttons=buttons)

async def show_mute_menu(event):
    muted = get_all_muted_users()
    buttons = []
    
    for uid, info in list(muted.items())[:10]:
        buttons.append([Button.inline(f"🔓 Unmute {info['user_name']}", f'mute_un_{uid}'.encode())])
        
    buttons.append([Button.inline('🔙 𝐁𝐚𝐜𝐤', b'main_menu')])
    await event.edit(f"🔇 **𝐌𝐔𝐓𝐄𝐃 𝐔𝐒𝐄𝐑𝐒** ({len(muted)})\nClick to unmute:", buttons=buttons)

async def show_about_menu(event):
    config = load_about_config()
    status = "✅ 𝐎𝐍" if config.get('enabled') else "❌ 𝐎𝐅𝐅"
    
    audio_pos = config.get('audio_position', 'after')
    pos_text = {
        'before': '⬅️ 𝐁𝐞𝐟𝐨𝐫𝐞',
        'after': '➡️ 𝐀𝐟𝐭𝐞𝐫',
        'none': '❌ 𝐍𝐨𝐧𝐞'
    }.get(audio_pos, '➡️ 𝐀𝐟𝐭𝐞𝐫')
    
    buttons = [
        [Button.inline(f'⚡ 𝐄𝐧𝐚𝐛𝐥𝐞𝐝: {status}', b'abt_toggle')],
        [Button.inline('✏️ 𝐄𝐝𝐢𝐭 𝐓𝐞𝐱𝐭', b'abt_edit_text')],
        [Button.inline('🖼️ 𝐒𝐞𝐭 𝐌𝐞𝐝𝐢𝐚', b'abt_set_media'), Button.inline('🎵 𝐒𝐞𝐭 𝐀𝐮𝐝𝐢𝐨', b'abt_set_audio')],
        [Button.inline(f'📍 𝐀𝐮𝐝𝐢𝐨 𝐏𝐨𝐬: {pos_text}', b'abt_audio_pos')],
        [Button.inline('🧹 𝐑𝐞𝐬𝐞𝐭 𝐒𝐞𝐞𝐧', b'abt_reset')],
        [Button.inline('🔙 𝐁𝐚𝐜𝐤', b'main_menu')]
    ]
    
    preview = config.get('text', 'No text set')[:100]
    media_status = '✅ Set' if config.get('media_path') else '❌ None'
    audio_status = '✅ Set' if config.get('audio_path') else '❌ None'
    
    text = f"👋 **𝐁𝐈𝐎 / 𝐀𝐔𝐓𝐎-𝐑𝐄𝐏𝐋𝐘**\n\n📜 **𝐓𝐞𝐱𝐭:**\n`{preview}`\n\n🖼️ **𝐌𝐞𝐝𝐢𝐚:** {media_status}\n🎵 **𝐀𝐮𝐝𝐢𝐨:** {audio_status}\n📍 **𝐏𝐨𝐬:** {pos_text}\n👀 **𝐒𝐞𝐞𝐧:** {len(config.get('seen_users', []))} users"
    
    if hasattr(event, 'data') and event.data:
        try:
            await event.edit(text, buttons=buttons)
        except:
            await event.respond(text, buttons=buttons)
    else:
        msg = await event.respond(text, buttons=buttons)
        if event.chat_id:
            last_menu_msg[event.chat_id] = msg.id

@bot.on(events.NewMessage(pattern='/start'))
async def bot_start_handler(event):
    if OWNER_ID and event.sender_id != OWNER_ID:
        return
    
    try:
        await event.delete()
    except:
        pass
        
    if event.chat_id in last_menu_msg:
        try:
            await bot.delete_messages(event.chat_id, last_menu_msg[event.chat_id])
        except:
            pass
            
    msg = await show_main_menu(event)
    if msg:
        last_menu_msg[event.chat_id] = msg.id

@bot.on(events.CallbackQuery)
async def bot_callback_handler(event):
    if OWNER_ID and event.sender_id != OWNER_ID:
        await event.answer('❌ Access Denied', alert=True)
        return
    
    data = event.data.decode('utf-8')
    
    # --- ROUTING ---
    if data == 'main_menu':
        await show_main_menu(event)
    elif data == 'menu_ai':
        await show_ai_menu(event)
    elif data == 'menu_saver':
        await show_saver_menu(event)
    elif data == 'menu_anim':
        await show_anim_menu(event)
    elif data == 'menu_mute':
        await show_mute_menu(event)
    elif data == 'menu_about':
        await show_about_menu(event)
    elif data == 'sys_status':
        import platform
        await event.answer(f"🐍 Python: {platform.python_version()}\n💻 OS: {platform.system()}\n🤖 Bot Active", alert=True)

    # --- AI ACTIONS ---
    elif data == 'ai_toggle_main':
        c = load_ai_config()
        c['enabled'] = not c.get('enabled', False)
        save_ai_config(c)
        await show_ai_menu(event)
    elif data == 'ai_toggle_voice':
        c = load_ai_config()
        c.setdefault('advanced', {})['voice_enabled'] = not c['advanced'].get('voice_enabled', True)
        save_ai_config(c)
        await show_ai_menu(event)
    elif data == 'ai_toggle_photo':
        c = load_ai_config()
        c.setdefault('advanced', {})['photo_enabled'] = not c['advanced'].get('photo_enabled', True)
        save_ai_config(c)
        await show_ai_menu(event)
    elif data == 'ai_toggle_auto':
        c = load_ai_config()
        c.setdefault('advanced', {})['auto_reply_all'] = not c['advanced'].get('auto_reply_all', False)
        save_ai_config(c)
        await show_ai_menu(event)
    elif data == 'ai_toggle_lower':
        c = load_ai_config()
        c.setdefault('advanced', {})['lowercase'] = not c['advanced'].get('lowercase', True)
        save_ai_config(c)
        await show_ai_menu(event)
    elif data == 'ai_toggle_priv':
        c = load_ai_config()
        c['ai_private_enabled'] = not c.get('ai_private_enabled', False)
        save_ai_config(c)
        await show_ai_menu(event)
    elif data == 'ai_toggle_grp':
        c = load_ai_config()
        c['ai_groups_enabled'] = not c.get('ai_groups_enabled', False)
        save_ai_config(c)
        await show_ai_menu(event)
    elif data in ['ai_sched_info', 'ai_temp_info', 'ai_hist_info']:
        await event.answer("ℹ️ Use commands to configure:\n.aiconfig schedule 10 22\n.aiconfig (edit JSON)", alert=True)

    # --- SAVER ACTIONS ---
    elif data.startswith('svr_') and data not in ['svr_browse', 'svr_clear_all', 'svr_clear_text', 'svr_clear_photo', 'svr_clear_video', 'svr_clear_voice'] and not data.startswith('svr_page') and not data.startswith('svr_view') and not data.startswith('svr_u_'):
        c = load_saver_config()
        k = {
            'svr_text': 'save_text',
            'svr_media': 'save_media',
            'svr_voice': 'save_voice',
            'svr_ttl': 'save_ttl_media',
            'svr_bots': 'save_bots',
            'svr_priv': 'save_private',
            'svr_grp': 'save_groups'
        }.get(data)
        if k:
            d = True if k not in ['save_ttl_media', 'save_bots', 'save_private', 'save_groups'] else False
            c[k] = not c.get(k, d)
            save_saver_config(c)
        await show_saver_menu(event)
        
    elif data == 'svr_browse':
        await show_saver_browser(event)
    elif data.startswith('svr_page_'):
        await show_saver_browser(event, int(data.split('_')[2]))
    elif data.startswith('svr_view_'):
        await show_deleted_for_user(event, int(data.split('_')[2]))
    elif data.startswith('svr_u_'):
        p = data.split('_')
        await show_deleted_for_user(event, int(p[2]), int(p[3]))
    elif data == 'svr_clear_all':
        clear_deleted_messages_by_type(None, 'all_global')
        await event.answer("✅ All deleted messages cleared!", alert=True)
        await show_saver_menu(event)
    elif data == 'svr_clear_text':
        db = load_deleted_messages_db()
        for chat_key in list(db.keys()):
            clear_deleted_messages_by_type(int(chat_key), 'text')
        await event.answer("✅ Text messages cleared!", alert=True)
        await show_saver_menu(event)
    elif data == 'svr_clear_photo':
        db = load_deleted_messages_db()
        for chat_key in list(db.keys()):
            clear_deleted_messages_by_type(int(chat_key), 'photo')
        await event.answer("✅ Photos cleared!", alert=True)
        await show_saver_menu(event)
    elif data == 'svr_clear_video':
        db = load_deleted_messages_db()
        for chat_key in list(db.keys()):
            clear_deleted_messages_by_type(int(chat_key), 'video')
        await event.answer("✅ Videos cleared!", alert=True)
        await show_saver_menu(event)
    elif data == 'svr_clear_voice':
        db = load_deleted_messages_db()
        for chat_key in list(db.keys()):
            clear_deleted_messages_by_type(int(chat_key), 'voice')
        await event.answer("✅ Voice messages cleared!", alert=True)
        await show_saver_menu(event)

    # --- ANIM ACTIONS ---
    elif data.startswith('anim_'):
        config = load_animation_config()
        chat_str = str(event.chat_id)
        if chat_str not in config:
            config[chat_str] = {'mode': None, 'font': None, 'duration': 40, 'interval': 0.5}
        
        if data == 'anim_rainbow':
            config[chat_str]['mode'] = 'rainbow' if config[chat_str]['mode'] != 'rainbow' else None
        elif data == 'anim_caps':
            config[chat_str]['mode'] = 'caps' if config[chat_str]['mode'] != 'caps' else None
        elif data == 'anim_font_menu':
            save_animation_config(config)
            await show_font_menu(event)
            return
        elif data == 'anim_dur_plus':
            config[chat_str]['duration'] += 10
        elif data == 'anim_dur_minus':
            config[chat_str]['duration'] = max(10, config[chat_str]['duration'] - 10)
        elif data == 'anim_int_plus':
            config[chat_str]['interval'] += 0.5
        elif data == 'anim_int_minus':
            config[chat_str]['interval'] = max(0.5, config[chat_str]['interval'] - 0.5)
        
        save_animation_config(config)
        await show_anim_menu(event)
    
    # --- FONT ACTIONS ---
    elif data.startswith('font_'):
        font = data.split('_')[1]
        if font == 'none':
            font = None
        
        config = load_animation_config()
        chat_str = str(event.chat_id)
        if chat_str not in config:
            config[chat_str] = {'mode': None, 'duration': 40, 'interval': 0.5}
        config[chat_str]['font'] = font
        save_animation_config(config)
        await show_anim_menu(event)

    # --- MUTE ACTIONS ---
    elif data.startswith('mute_un_'):
        uid = int(data.split('_')[2])
        unmute_user_new(uid)
        await event.answer("✅ Unmuted!", alert=True)
        await show_mute_menu(event)

    # --- BIO ACTIONS ---
    elif data == 'abt_toggle':
        c = load_about_config()
        c['enabled'] = not c.get('enabled', False)
        save_about_config(c)
        await show_about_menu(event)
    elif data == 'abt_reset':
        c = load_about_config()
        c['seen_users'] = []
        save_about_config(c)
        await event.answer("✅ History cleared!", alert=True)
        await show_about_menu(event)
    elif data == 'abt_edit_text':
        bio_state[event.chat_id] = 'waiting_text'
        await event.edit("✏️ **Send me the new Bio text now.**\n\n[Waiting for input...]", buttons=[[Button.inline('🔙 Cancel', b'menu_about')]])
    elif data == 'abt_set_media':
        bio_state[event.chat_id] = 'waiting_media'
        await event.edit("🖼️ **Send me the photo/gif/video now.**\n\n[Waiting for input...]", buttons=[[Button.inline('🔙 Cancel', b'menu_about')]])
    elif data == 'abt_set_audio':
        bio_state[event.chat_id] = 'waiting_audio'
        await event.edit("🎵 **Send me the Audio/Voice now.**\n\n[Waiting for input...]", buttons=[[Button.inline('🔙 Cancel', b'menu_about')]])
    elif data == 'abt_audio_pos':
        c = load_about_config()
        positions = ['before', 'after', 'none']
        current = c.get('audio_position', 'after')
        current_idx = positions.index(current) if current in positions else 1
        next_pos = positions[(current_idx + 1) % len(positions)]
        c['audio_position'] = next_pos
        save_about_config(c)
        await show_about_menu(event)

@bot.on(events.NewMessage(incoming=True))
async def bot_message_handler(event):
    if OWNER_ID and event.sender_id != OWNER_ID:
        return
    if not event.is_private:
        return
    
    state = bio_state.get(event.chat_id)
    if not state:
        return
    
    if state == 'waiting_text':
        c = load_about_config()
        c['text'] = event.text
        save_about_config(c)
        bio_state.pop(event.chat_id, None)
        
        try:
            await event.delete()
        except:
            pass
        
        msg = await event.respond("✅ Text updated!", buttons=[[Button.inline('🔙 Back', b'menu_about')]])
        await asyncio.sleep(2)
        try:
            await msg.delete()
            await show_about_menu(event)
        except:
            pass
        
    elif state == 'waiting_media':
        if event.media:
            path = await event.download_media(file='saved_media/bio_media')
            c = load_about_config()
            c['media_path'] = path
            save_about_config(c)
            bio_state.pop(event.chat_id, None)
            
            try:
                await event.delete()
            except:
                pass
            
            msg = await event.respond("✅ Media updated!", buttons=[[Button.inline('🔙 Back', b'menu_about')]])
            await asyncio.sleep(2)
            try:
                await msg.delete()
                await show_about_menu(event)
            except:
                pass
        else:
            msg = await event.respond("❌ No media found!")
            await asyncio.sleep(2)
            await msg.delete()
            
    elif state == 'waiting_audio':
        if event.media:
            ext = 'ogg'
            if event.voice:
                ext = 'ogg'
            elif event.audio:
                ext = 'mp3'
            
            path = await event.download_media(file=f'saved_media/bio_audio.{ext}')
            c = load_about_config()
            c['audio_path'] = path
            save_about_config(c)
            bio_state.pop(event.chat_id, None)
            
            try:
                await event.delete()
            except:
                pass
            
            msg = await event.respond("✅ Audio updated!", buttons=[[Button.inline('🔙 Back', b'menu_about')]])
            await asyncio.sleep(2)
            try:
                await msg.delete()
                await show_about_menu(event)
            except:
                pass
        else:
            msg = await event.respond("❌ No audio found!")
            await asyncio.sleep(2)
            await msg.delete()

async def delete_previous_command(chat_id):
    """Удалить предыдущее командное сообщение"""
    if chat_id in last_command_message:
        try:
            msg_ids = last_command_message[chat_id]
            await client.delete_messages(chat_id, msg_ids if isinstance(msg_ids, list) else [msg_ids])
        except:
            pass

async def register_command_message(chat_id, message_id):
    """Зарегистрировать командное сообщение для удаления"""
    last_command_message[chat_id] = message_id

async def forward_to_saved(media_path, caption_text=""):
    """Пересылка медиа в избранное"""
    try:
        if not media_path or not os.path.exists(media_path):
            print(f'⚠️ Файл не найден: {media_path}')
            return False
        
        await client.send_file('me', media_path, caption=caption_text)
        print(f'📤 Переслано в избранное: {os.path.basename(media_path)}')
        return True
    except Exception as e:
        print(f'⚠️ Ошибка пересылки в избранное: {e}')
        import traceback
        traceback.print_exc()
        return False

async def send_bio_message(event):
    """Отправка Bio сообщения (Текст/Медиа + Аудио)"""
    about_config = load_about_config()
    if not about_config.get('enabled'):
        return False

    text = about_config.get('text', '')
    media_path = about_config.get('media_path')
    audio_path = about_config.get('audio_path')
    audio_pos = about_config.get('audio_position', 'after')
    
    try:
        # Отправка аудио до
        if audio_pos == 'before' and audio_path and os.path.exists(audio_path):
            await event.client.send_file(event.chat_id, audio_path)
            await asyncio.sleep(0.3)
        
        # Основное сообщение
        if media_path and os.path.exists(media_path):
            await event.client.send_file(event.chat_id, media_path, caption=text if text else None)
        elif text:
            await event.client.send_message(event.chat_id, text)
        
        # Отправка аудио после
        if audio_pos == 'after' and audio_path and os.path.exists(audio_path):
            await asyncio.sleep(0.3)
            await event.client.send_file(event.chat_id, audio_path)
    except Exception as e:
        print(f"Bio Send Error: {e}")
    
    return True

# ============ ОБРАБОТЧИКИ КОМАНД ============
async def handle_aiconfig_commands(event, message_text):
    """Обработка команд настройки ИИ"""
    chat_id = event.chat_id
    message_text = message_text.strip()
    
    await delete_previous_command(chat_id)
    
    if message_text.lower() == '.aiconfig help':
        help_text = '''🤖 **ПАНЕЛЬ УПРАВЛЕНИЯ ИИ** (OnlySQ API)

📋 **ОСНОВНЫЕ НАСТРОЙКИ**
┣‣ `.aiconfig status` - 📊 Показать статус
┣‣ `.aiconfig on/off` - 🔌 Вкл/выкл ИИ
┣‣ `.aiconfig auto on/off` - 🤖 Авто-ответ всем
┣‣ `.aiconfig voice on/off` - 🎤 Голосовые
┣‣ `.aiconfig photo on/off` - 📷 Фото

⚙️ **КОНФИГУРАЦИЯ**
┣‣ `.aiconfig show` - 📄 Показать конфиг
┣‣ `.aiconfig export` - 💾 Экспорт в JSON
┣‣ `.aiconfig edit` - ✏️ Редактировать
┣‣ `.aiconfig reset` - 🔄 Сброс
┣‣ Отправьте JSON файл - загрузка конфига

💡 **СТИЛЬ**
┣‣ `.aiconfig lowercase on/off` - 🔡 Маленькие буквы

📝 **ЛИЧНОСТЬ**
┣‣ `.aiconfig personality <текст>` - Задать личность

🗑️ **УПРАВЛЕНИЕ**
┣‣ `.aistop` - ❌ Выключить в чате
┣‣ `.aiclear` - 🗑️ Очистить историю

⚡ **БЫСТРЫЕ ЗАПРОСЫ**
┣‣ `.neiro <запрос>` - Мгновенный ответ

📌 **ПРОДВИНУТЫЕ**
┣‣ Параметр `temperature` (0.1-2.0)
┣‣ Параметр `max_history` (1-100)
┣‣ Редактируйте через JSON файл

🌐 **API:** OnlySQ
🤖 **Модель:** gpt-4o-mini'''
        
        msg = await event.respond(help_text)
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.aiconfig status':
        config = load_ai_config()
        advanced = config.get('advanced', {})
        status_text = f'''🤖 **СТАТУС ИИ:**

🔌 Состояние: {"✅ ВКЛЮЧЕН" if config.get('enabled', False) else "❌ ВЫКЛЮЧЕН"}
🧠 Личность: {config.get('personality', 'не задана')[:80]}...

**ПРОДВИНУТЫЕ НАСТРОЙКИ:**
🤖 Авто-ответ: {"✅" if advanced.get('auto_reply_all', False) else "❌"}
🎤 Голосовые: {"✅" if advanced.get('voice_enabled', True) else "❌"}
📷 Фото: {"✅" if advanced.get('photo_enabled', True) else "❌"}
🔡 Маленькие буквы: {"✅" if advanced.get('lowercase', True) else "❌"}
📊 История: {advanced.get('max_history', 20)} сообщений
🌡️ Temperature: {advanced.get('temperature', 0.7)}

🌐 **API:** OnlySQ
🤖 **Модель:** {MODEL_NAME}
⚡ **Быстрые запросы:** .neiro <текст>'''
        
        msg = await event.respond(status_text)
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() in ['.aiconfig on', '.aiconfig off']:
        config = load_ai_config()
        config['enabled'] = 'on' in message_text.lower()
        save_ai_config(config)
        
        status = "✅ ИИ включен" if config['enabled'] else "❌ ИИ выключен"
        msg = await event.respond(status)
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() in ['.aiconfig auto on', '.aiconfig auto off']:
        config = load_ai_config()
        if 'advanced' not in config:
            config['advanced'] = {}
        config['advanced']['auto_reply_all'] = 'on' in message_text.lower()
        save_ai_config(config)
        
        msg = await event.respond(f'{"✅ Авто-ответ всем включен" if config["advanced"]["auto_reply_all"] else "❌ Авто-ответ всем выключен"}')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() in ['.aiconfig voice on', '.aiconfig voice off']:
        config = load_ai_config()
        if 'advanced' not in config:
            config['advanced'] = {}
        config['advanced']['voice_enabled'] = 'on' in message_text.lower()
        save_ai_config(config)
        
        msg = await event.respond(f'{"✅ Обработка голосовых включена" if config["advanced"]["voice_enabled"] else "❌ Обработка голосовых выключена"}')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() in ['.aiconfig photo on', '.aiconfig photo off']:
        config = load_ai_config()
        if 'advanced' not in config:
            config['advanced'] = {}
        config['advanced']['photo_enabled'] = 'on' in message_text.lower()
        save_ai_config(config)
        
        msg = await event.respond(f'{"✅ Обработка фото включена" if config["advanced"]["photo_enabled"] else "❌ Обработка фото выключена"}')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() in ['.aiconfig lowercase on', '.aiconfig lowercase off']:
        config = load_ai_config()
        if 'advanced' not in config:
            config['advanced'] = {}
        config['advanced']['lowercase'] = 'on' in message_text.lower()
        save_ai_config(config)
        
        msg = await event.respond(f'{"✅ Маленькие буквы включены" if config["advanced"]["lowercase"] else "❌ Маленькие буквы выключены"}')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower().startswith('.aiconfig personality '):
        personality = message_text[len('.aiconfig personality '):].strip()
        if not personality:
            msg = await event.respond('❌ Укажите текст личности')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
        
        config = load_ai_config()
        config['personality'] = personality
        save_ai_config(config)
        
        msg = await event.respond(f'✅ Личность обновлена:\n{personality[:200]}')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.aiconfig show':
        config = load_ai_config()
        config_text = json.dumps(config, ensure_ascii=False, indent=2)
        
        msg = await event.respond(f'```json\n{config_text}\n```')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.aiconfig export':
        config = load_ai_config()
        config_text = json.dumps(config, ensure_ascii=False, indent=2)
        
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json', delete=False) as f:
            f.write(config_text)
            temp_path = f.name
        
        try:
            await client.send_file(chat_id, temp_path, caption='📤 **Экспорт конфигурации ИИ**\n\nЧтобы загрузить обратно, просто отправьте этот файл')
            await event.delete()
            os.unlink(temp_path)
        except Exception as e:
            msg = await event.respond(f'❌ Ошибка экспорта: {e}')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            try:
                os.unlink(temp_path)
            except:
                pass
        return True
    
    if message_text.lower() == '.aiconfig edit':
        config = load_ai_config()
        config_text = json.dumps(config, ensure_ascii=False, indent=2)
        
        help_msg = '''✏️ **РЕДАКТИРОВАНИЕ КОНФИГА**

Текущий конфиг:
```json
{}```

**Как редактировать:**
1. Скопируйте JSON выше
2. Отредактируйте параметры
3. Сохраните в файл `.json`
4. Отправьте файл сюда

**Или используйте `.aiconfig export`** для скачивания файла'''.format(config_text)
        
        msg = await event.respond(help_msg)
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.aiconfig reset':
        default_config = {
            'enabled': False,
            'personality': 'отвечай как обычный человек, кратко и по делу. пиши с маленькой буквы'
        }
        save_ai_config(default_config)
        
        msg = await event.respond('🔄 Конфигурация сброшена до базовой (2 параметра)\n\n💡 Используйте `.aiconfig help` для настройки')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True

    if message_text.lower() in ['.aiconfig private on', '.aiconfig private off']:
        config = load_ai_config()
        config['ai_private_enabled'] = 'on' in message_text.lower()
        save_ai_config(config)
        msg = await event.respond(f'{"✅" if config["ai_private_enabled"] else "❌"} ИИ в личных чатах')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True

    if message_text.lower() in ['.aiconfig groups on', '.aiconfig groups off']:
        config = load_ai_config()
        config['ai_groups_enabled'] = 'on' in message_text.lower()
        save_ai_config(config)
        msg = await event.respond(f'{"✅" if config["ai_groups_enabled"] else "❌"} ИИ в группах')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True

    if message_text.lower() == '.aiconfig add':
        activate_chat(chat_id)
        msg = await event.respond('✅ Чат добавлен в разрешенные для ИИ!')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
        
    if message_text.lower() == '.aiconfig remove':
        deactivate_chat(chat_id)
        msg = await event.respond('❌ Чат удален из разрешенных для ИИ!')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True

    if message_text.lower().startswith('.aiconfig schedule '):
        try:
            parts = message_text.split()
            if len(parts) != 4:
                raise ValueError
            start = int(parts[2])
            end = int(parts[3])
            
            config = load_ai_config()
            config['schedule'] = {'start': start, 'end': end}
            save_ai_config(config)
            
            msg = await event.respond(f'⏰ Расписание установлено: с {start}:00 до {end}:00')
        except:
            msg = await event.respond('❌ Формат: `.aiconfig schedule <начало> <конец>` (в часах, например `1 6`)')
        
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    return False

async def handle_mute_commands_new(event, message_text):
    """Обработка команд заглушки/разглушки"""
    chat_id = event.chat_id
    message_text = message_text.strip()
    
    await delete_previous_command(chat_id)
    
    if message_text.lower() == '.список':
        muted = get_all_muted_users()
        if not muted:
            msg = await event.respond('📭 Нет заглушенных пользователей')
        else:
            list_text = f'🔇 **ЗАГЛУШЕННЫЕ ({len(muted)}):**\n\n'
            for i, (user_id, info) in enumerate(muted.items(), 1):
                list_text += f'{i}. {info.get("user_name", "?")} (ID: `{user_id}`)\n'
                list_text += f'   📅 {info.get("muted_at", "")[:16]}\n\n'
            list_text += '\n💡 Чтобы разглушить:\n'
            list_text += '• Ответьте на сообщение командой `.говори`\n'
            list_text += '• Или используйте `.говори <ID>`'
            
            msg = await event.respond(list_text)
        
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.замолчи':
        if event.reply_to_msg_id:
            try:
                reply_msg = await event.get_reply_message()
                user_id = reply_msg.sender_id
                
                if user_id == OWNER_ID:
                    msg = await event.respond('❌ Нельзя заглушить самого себя!')
                    await event.delete()
                    await register_command_message(chat_id, msg.id)
                    return True
                
                sender = await reply_msg.get_sender()
                user_name = getattr(sender, 'first_name', 'Неизвестно')
                if hasattr(sender, 'username') and sender.username:
                    user_name += f' (@{sender.username})'
                
                mute_user_new(user_id, user_name, reply_msg.chat_id)
                
                msg = await event.respond(f'🔇 **{user_name}** заглушен глобально!\n\n💡 Его сообщения теперь игнорируются везде\n📝 Разглушить: `.говори` (ответом) или `.говори {user_id}`')
                await event.delete()
                await register_command_message(chat_id, msg.id)
                return True
            except Exception as e:
                msg = await event.respond(f'❌ Ошибка: {e}')
                await event.delete()
                await register_command_message(chat_id, msg.id)
                return True
        else:
            msg = await event.respond('❌ Ответьте на сообщение пользователя командой `.замолчи`!')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
    
    if message_text.lower().startswith('.говори'):
        if event.reply_to_msg_id:
            try:
                reply_msg = await event.get_reply_message()
                user_id = reply_msg.sender_id
                user_info = unmute_user_new(user_id)
                
                if user_info:
                    msg = await event.respond(f'🔊 **{user_info.get("user_name")}** разглушен!\n\n💡 Сообщения снова обрабатываются')
                else:
                    msg = await event.respond('⚠️ Пользователь не был заглушен!')
                
                await event.delete()
                await register_command_message(chat_id, msg.id)
                return True
            except Exception as e:
                msg = await event.respond(f'❌ Ошибка: {e}')
                await event.delete()
                await register_command_message(chat_id, msg.id)
                return True
        
        parts = message_text.split()
        if len(parts) >= 2:
            try:
                user_id = int(parts[1])
                user_info = unmute_user_new(user_id)
                
                if user_info:
                    msg = await event.respond(f'🔊 **{user_info.get("user_name")}** разглушен!\n\n💡 Сообщения снова обрабатываются')
                else:
                    msg = await event.respond(f'⚠️ Пользователь {user_id} не был заглушен!')
                
                await event.delete()
                await register_command_message(chat_id, msg.id)
                return True
            except ValueError:
                msg = await event.respond('❌ Неверный формат ID!')
                await event.delete()
                await register_command_message(chat_id, msg.id)
                return True
        else:
            msg = await event.respond('❌ Используйте: `.говори <ID>` или ответьте на сообщение')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
    
    return False

async def handle_saver_commands(event, message_text):
    chat_id = event.chat_id
    await delete_previous_command(chat_id)
    
    if message_text.lower() == '.saver help':
        help_text = '''🔧 **ПАНЕЛЬ УПРАВЛЕНИЯ СОХРАНЕНИЕМ**

💡 *Сохраняет удалённые сообщения*

📋 **НАСТРОЙКИ**
┣‣ `.saver status` - 📊 Статус
┣‣ `.saver private on/off` - 🔓 Личные
┣‣ `.saver groups on/off` - 👥 Группы
┣‣ `.saver add` - ➕ Добавить чат
┣‣ `.saver remove` - ➖ Удалить чат

🗑️ **УДАЛЁННЫЕ**
┣‣ `.saver show` - 📄 Последние 10
┣‣ `.saver all` - 👥 Все пользователи
┣‣ `.saver user <номер>` - 📂 Все сообщения

🧹 **ОЧИСТКА**
┣‣ `.saver clear all` - 🗑️ Вся база
┣‣ `.saver clear text` - 📝 Текст
┣‣ `.saver clear photo` - 🖼️ Фото
┣‣ `.saver clear video` - 🎥 Видео
┣‣ `.saver clear voice` - 🎤 ГС
┣‣ `.saver clear user <номер>` - 👤 Пользователь

⚙️ **ТИПЫ**
┣‣ `.saver text on/off` - 📝 Текст
┣‣ `.saver media on/off` - 🖼️ Медиа
┣‣ `.saver voice on/off` - 🎤 Голосовые
┣‣ `.saver ttl on/off` - ⏱️ Скоротечные
┣‣ `.saver bots on/off` - 🤖 Боты

💡 *Медиа пересылается в избранное*'''
        msg = await event.respond(help_text)
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.saver status':
        config = load_saver_config()
        is_private, is_group = event.is_private, event.is_group
        is_saved = should_save_message(chat_id, is_private, is_group)
        status_text = f'📊 **СТАТУС СОХРАНЕНИЯ:**\n\n'
        status_text += f'📍 Текущий чат: {"✅ ВКЛ" if is_saved else "❌ ВЫКЛ"}\n'
        status_text += f'💬 Личные: {"✅" if config["save_private"] else "❌"}\n'
        status_text += f'👥 Группы: {"✅" if config["save_groups"] else "❌"}\n'
        status_text += f'📑 Каналы: {len(config["save_channels"])} шт.\n\n'
        status_text += f'**ТИПЫ:**\n'
        status_text += f'📝 Текст: {"✅" if config.get("save_text", True) else "❌"}\n'
        status_text += f'🖼️ Медиа: {"✅" if config.get("save_media", True) else "❌"}\n'
        status_text += f'🎤 Голосовые: {"✅" if config.get("save_voice", True) else "❌"}\n'
        status_text += f'⏱️ Скоротечные: {"✅" if config.get("save_ttl_media", False) else "❌"}\n'
        status_text += f'🤖 Боты: {"✅" if config.get("save_bots", False) else "❌"}'
        msg = await event.respond(status_text)
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() in ['.saver text on', '.saver text off']:
        config = load_saver_config()
        config['save_text'] = 'on' in message_text
        save_saver_config(config)
        msg = await event.respond(f'{"✅" if config["save_text"] else "❌"} Сохранение текста')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() in ['.saver media on', '.saver media off']:
        config = load_saver_config()
        config['save_media'] = 'on' in message_text
        save_saver_config(config)
        msg = await event.respond(f'{"✅" if config["save_media"] else "❌"} Сохранение медиа')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() in ['.saver voice on', '.saver voice off']:
        config = load_saver_config()
        config['save_voice'] = 'on' in message_text
        save_saver_config(config)
        msg = await event.respond(f'{"✅" if config["save_voice"] else "❌"} Сохранение голосовых')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() in ['.saver ttl on', '.saver ttl off']:
        config = load_saver_config()
        config['save_ttl_media'] = 'on' in message_text
        save_saver_config(config)
        msg = await event.respond(f'{"✅" if config["save_ttl_media"] else "❌"} Сохранение скоротечных')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() in ['.saver bots on', '.saver bots off']:
        config = load_saver_config()
        config['save_bots'] = 'on' in message_text
        save_saver_config(config)
        msg = await event.respond(f'{"✅" if config["save_bots"] else "❌"} Сохранение сообщений ботов')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() in ['.saver private on', '.saver private off']:
        config = load_saver_config()
        config['save_private'] = 'on' in message_text
        save_saver_config(config)
        msg = await event.respond(f'{"✅" if config["save_private"] else "❌"} Личные чаты')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() in ['.saver groups on', '.saver groups off']:
        config = load_saver_config()
        config['save_groups'] = 'on' in message_text
        save_saver_config(config)
        msg = await event.respond(f'{"✅" if config["save_groups"] else "❌"} Группы')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.saver add':
        config = load_saver_config()
        chat_id_str = str(chat_id)
        if chat_id_str not in config['save_channels']:
            config['save_channels'].append(chat_id_str)
            save_saver_config(config)
            msg = await event.respond(f'✅ Чат добавлен!')
        else:
            msg = await event.respond(f'⚠️ Уже добавлен!')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.saver remove':
        config = load_saver_config()
        chat_id_str = str(chat_id)
        if chat_id_str in config['save_channels']:
            config['save_channels'].remove(chat_id_str)
            save_saver_config(config)
            msg = await event.respond(f'❌ Чат удален!')
        else:
            msg = await event.respond(f'⚠️ Не был добавлен!')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.saver show':
        msgs = get_deleted_messages(limit=10)
        if not msgs:
            msg = await event.respond('📭 Нет удаленных сообщений')
        else:
            response = f'🗑️ **Последние {len(msgs)} удалённых:**\n\n'
            for i, m in enumerate(msgs, 1):
                sender_name = m.get('sender_name', 'Неизвестно')
                sender_id = m.get('sender_id', '?')
                text_type = "📝"
                if m.get('has_photo'): text_type = "🖼️"
                elif m.get('has_video'): text_type = "🎥"
                elif m.get('has_document'): text_type = "📄"
                elif m.get('has_voice'): text_type = "🎤"
                
                date_str = m.get("deleted_at", "")[:16].replace('T', ' ')
                
                response += f'{i}. {text_type} **{sender_name}** (`{sender_id}`)\n'
                response += f'   🕒 {date_str}\n'
                response += f'   💬 {m.get("text", "")[:50]}\n\n'
            msg = await event.respond(response)
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.saver clear all':
        clear_deleted_messages_by_type(None, 'all_global')
        msg = await event.respond('🗑️ Вся база очищена!')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.saver clear text':
        db = load_deleted_messages_db()
        for chat_key in list(db.keys()):
            clear_deleted_messages_by_type(int(chat_key), 'text')
        msg = await event.respond('🗑️ Текстовые сообщения очищены!')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.saver clear photo':
        db = load_deleted_messages_db()
        for chat_key in list(db.keys()):
            clear_deleted_messages_by_type(int(chat_key), 'photo')
        msg = await event.respond('🗑️ Фото очищены!')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.saver clear video':
        db = load_deleted_messages_db()
        for chat_key in list(db.keys()):
            clear_deleted_messages_by_type(int(chat_key), 'video')
        msg = await event.respond('🗑️ Видео очищены!')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.saver clear voice':
        db = load_deleted_messages_db()
        for chat_key in list(db.keys()):
            clear_deleted_messages_by_type(int(chat_key), 'voice')
        msg = await event.respond('🗑️ Голосовые очищены!')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True

    if message_text.lower().startswith('.saver clear user '):
        try:
            parts = message_text.split()
            if len(parts) < 4:
                msg = await event.respond('❌ Формат: `.saver clear user <номер>`')
                await event.delete()
                await register_command_message(chat_id, msg.id)
                return True
            
            index = int(parts[3]) - 1
            users = load_temp_selection(chat_id)
            if users is None:
                msg = await event.respond('⚠️ Сначала вызовите `.saver all`')
                await event.delete()
                await register_command_message(chat_id, msg.id)
                return True
            
            if 0 <= index < len(users):
                sender_id = users[index]['sender_id']
                sender_name = users[index]['name']
                clear_deleted_messages_by_type(chat_id, None, None, sender_id)
                msg = await event.respond(f'🗑️ Сообщения **{sender_name}** удалены!')
            else:
                msg = await event.respond('❌ Неверный номер')
            
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
        except Exception as e:
            msg = await event.respond(f'❌ Ошибка: {e}')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
    
    if message_text.lower() == '.saver all':
        if not event.is_private:
            msg = await event.respond('❌ Команда доступна ТОЛЬКО в личном чате!')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
            
        senders = get_all_senders_with_deleted()
        if not senders:
            msg = await event.respond('📭 Нет пользователей с удалёнными')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
            
        users_list = [{'sender_id': sid, 'name': name} for sid, name, cnt in senders]
        save_temp_selection(chat_id, users_list)
        
        response = '👥 **ПОЛЬЗОВАТЕЛИ С УДАЛЁННЫМИ:**\n\n'
        for i, (sid, name, cnt) in enumerate(senders, 1):
            response += f'{i}. {name} — 🗑️ {cnt} шт.\n'
        response += '\n🔢 Введите номер или `.saver user <номер>`'
        
        msg = await event.respond(response)
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower().startswith('.saver user '):
        try:
            parts = message_text.split()
            if len(parts) < 3:
                msg = await event.respond('❌ Формат: `.saver user <ID или номер>`')
                await event.delete()
                await register_command_message(chat_id, msg.id)
                return True
            
            query = parts[2]
            
            if query.isdigit() and len(query) > 5:
                sender_id = int(query)
                msgs = get_deleted_messages(sender_id=sender_id)
                sender_name = f"ID {sender_id}"
                for m in msgs:
                    if m.get('sender_name'):
                        sender_name = m.get('sender_name')
                        break
            else:
                index = int(query) - 1
                users = load_temp_selection(chat_id)
                if users is None:
                    sender_id = int(query)
                    msgs = get_deleted_messages(sender_id=sender_id)
                    sender_name = f"ID {sender_id}"
                else: 
                    if 0 <= index < len(users):
                        sender_id = users[index]['sender_id']
                        sender_name = users[index]['name']
                        msgs = get_deleted_messages(sender_id=sender_id)
                    else:
                        msg = await event.respond('❌ Неверный номер')
                        await event.delete()
                        await register_command_message(chat_id, msg.id)
                        return True

            if not msgs:
                text = f'📭 У **{sender_name}** нет удалённых'
            else:
                text = f'🗑️ **{sender_name}** (`{sender_id}`)\n(ВСЕГО: {len(msgs)} шт.):\n\n'
                display_msgs = msgs[:20]
                for i, m in enumerate(display_msgs, 1):
                    text_type = "📝"
                    if m.get('has_photo'): text_type = "🖼️"
                    elif m.get('has_video'): text_type = "🎥"
                    elif m.get('has_document'): text_type = "📄"
                    elif m.get('has_voice'): text_type = "🎤"
                    
                    date_str = m.get("deleted_at", "")[:16].replace('T', ' ')
                    
                    text += f'{i}. {text_type} [{date_str}]\n'
                    text += f'   💬 {m.get("text", "")[:50]}\n\n'
                if len(msgs) > 20:
                    text += f'\n...ещё {len(msgs)-20} сообщений\n'
            msg = await event.respond(text)
            
            user_selection_state.pop(str(chat_id), None)
            
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
        except Exception as e:
            msg = await event.respond(f'❌ Ошибка: {e}')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
    
    return False

async def handle_digit_selection(event, message_text):
    chat_id = event.chat_id
    
    if not message_text.strip().isdigit():
        return False
        
    users = load_temp_selection(chat_id)
    if users is None:
        return False
        
    try:
        index = int(message_text.strip()) - 1
        if 0 <= index < len(users):
            sender_id = users[index]['sender_id']
            sender_name = users[index]['name']
            msgs = get_deleted_messages(sender_id=sender_id)
            
            if not msgs:
                text = f'📭 У **{sender_name}** нет удалённых'
            else:
                text = f'🗑️ **{sender_name}** (ВСЕГО: {len(msgs)} шт.):\n\n'
                display_msgs = msgs[:30]
                for i, m in enumerate(display_msgs, 1):
                    text_type = "📝"
                    if m.get('has_photo'): text_type = "🖼️"
                    elif m.get('has_video'): text_type = "🎥"
                    elif m.get('has_document'): text_type = "📄"
                    elif m.get('has_voice'): text_type = "🎤"
                    text += f'{i}. {text_type} [{m.get("deleted_at", "")[:16]}]\n'
                    text += f'   Чат: `{m.get("chat_id")}`\n'
                    text += f'   {m.get("text", "")[:50]}\n\n'
                if len(msgs) > 30:
                    text += f'\n...ещё {len(msgs)-30} сообщений'
                    
            msg = await event.respond(text)
            user_selection_state.pop(str(chat_id), None)
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
        else:
            msg = await event.respond('❌ Неверный номер')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
    except:
        return False

async def handle_neiro_command(event, message_text):
    """Обработка команды .neiro для быстрых запросов к ИИ"""
    try:
        if not message_text.lower().startswith('.neiro '):
            return False
        
        query = message_text[7:].strip()
        
        if not query:
            await event.edit('❌ Укажите запрос после .neiro')
            return True
        
        await event.edit(f'🤖 **Запрос:** {query}\n\n⏳ Думаю...')
        
        config = load_ai_config()
        
        messages = [{'role': 'user', 'content': query}]
        response = await get_ai_response(messages, config)
        
        formatted_response = f'🤖 **Запрос:** {query}\n\n📝 **Ответ:**\n```\n{response}\n```'
        
        await event.edit(formatted_response)
        
        return True
    except Exception as e:
        print(f'❌ Ошибка .neiro: {e}')
        try:
            await event.edit(f'❌ Ошибка: {e}')
        except:
            pass
        return True

async def handle_animation_commands(event, message_text):
    chat_id = event.chat_id
    await delete_previous_command(chat_id)
    
    if message_text.lower() == '.anim help':
        help_text = '''🎬 **КОМАНДЫ АНИМАЦИЙ**

**ТИПЫ:**
• rainbow 🌈 - радужная анимация
• caps 🔤 - чередование регистра

**ШРИФТЫ:**
• bold - 𝐁𝐨𝐥𝐝
• italic - 𝘐𝘵𝘢𝘭𝘪𝘤
• bolditalic - 𝑩𝒐𝒍𝒅 𝑰𝒕𝒂𝒍𝒊𝒄
• script - 𝒮𝒸𝓇𝒾𝓅𝓉
• fraktur - 𝔉𝔯𝔞𝔨𝔱𝔲𝔯
• smallcaps - ᴀᴧичноᴄᴛь

**ИСПОЛЬЗОВАНИЕ:**
`.anim <тип> <шрифт> текст`
Пример: `.anim rainbow smallcaps Привет!`
Без шрифта: `.anim rainbow Привет!`

**НАСТРОЙКИ:**
• `.anim mode <тип>` - авто-анимация
• `.anim mode off` - выключить
• `.anim font <шрифт>` - установить шрифт
• `.anim font off` - убрать шрифт
• `.anim duration <сек>` - длительность
• `.anim interval <сек>` - интервал
• `.anim status` - показать настройки'''
        msg = await event.respond(help_text)
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower() == '.anim status':
        settings = get_animation_settings(chat_id)
        mode = settings['mode']
        font = settings['font']
        status_text = f'🎬 **Статус:**\n'
        status_text += f'Режим: **{mode.upper() if mode else "ВЫКЛ"}**\n'
        status_text += f'Шрифт: **{font if font else "ВЫКЛ"}**\n'
        status_text += f'⏱️ Длительность: {settings["duration"]} сек\n'
        status_text += f'⏲️ Интервал: {settings["interval"]} сек'
        msg = await event.respond(status_text)
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower().startswith('.anim duration '):
        try:
            duration = float(message_text.split()[2])
            config = load_animation_config()
            chat_key = str(chat_id)
            if chat_key not in config:
                config[chat_key] = {'mode': None, 'font': None, 'interval': 0.5}
            config[chat_key]['duration'] = duration
            save_animation_config(config)
            msg = await event.respond(f'✅ Длительность: {duration} сек')
        except:
            msg = await event.respond('❌ Неверный формат')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower().startswith('.anim interval '):
        try:
            interval = float(message_text.split()[2])
            config = load_animation_config()
            chat_key = str(chat_id)
            if chat_key not in config:
                config[chat_key] = {'mode': None, 'font': None, 'duration': 40}
            config[chat_key]['interval'] = interval
            save_animation_config(config)
            msg = await event.respond(f'✅ Интервал: {interval} сек')
        except:
            msg = await event.respond('❌ Неверный формат')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower().startswith('.anim mode '):
        parts = message_text.split(maxsplit=2)
        if len(parts) < 3:
            msg = await event.respond('❌ Формат: `.anim mode <тип>`')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
            
        mode = parts[2].lower()
        if mode == 'off':
            set_animation_mode(chat_id, None)
            msg = await event.respond('❌ Режим ВЫКЛЮЧЕН')
        elif mode in ['rainbow', 'caps']:
            set_animation_mode(chat_id, mode)
            msg = await event.respond(f'✅ Режим **{mode.upper()}** включен!')
        else:
            msg = await event.respond('❌ Неизвестный режим!')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower().startswith('.anim font '):
        parts = message_text.split(maxsplit=2)
        if len(parts) < 3:
            msg = await event.respond('❌ Формат: `.anim font <шрифт>`')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return True
            
        font = parts[2].lower()
        if font == 'off':
            set_animation_mode(chat_id, get_animation_settings(chat_id)['mode'], None)
            msg = await event.respond('❌ Шрифт ВЫКЛЮЧЕН')
        elif font in FONTS:
            set_animation_mode(chat_id, get_animation_settings(chat_id)['mode'], font)
            msg = await event.respond(f'✅ Шрифт **{font}** установлен!')
        else:
            msg = await event.respond('❌ Неизвестный шрифт!')
        await event.delete()
        await register_command_message(chat_id, msg.id)
        return True
    
    if message_text.lower().startswith('.anim '):
        parts = message_text.split(maxsplit=3)
        if len(parts) >= 3:
            anim_type = parts[1].lower()
            
            # Проверяем, указан ли шрифт
            if len(parts) == 4 and parts[2] in FONTS:
                font = parts[2]
                text = parts[3]
            elif len(parts) == 3:
                font = None
                text = parts[2]
            else:
                return False
            
            if anim_type in ['rainbow', 'caps']:
                await event.delete()
                settings = get_animation_settings(chat_id)
                animation_msg = await event.respond('🎬 Запуск...')
                await run_animation(animation_msg, text, anim_type, settings['duration'], settings['interval'], font)
                return True
    
    return False

# ============ ОБРАБОТЧИКИ СОБЫТИЙ ============
@client.on(events.NewMessage(incoming=True, from_users=None))
async def immediate_save_handler(event):
    """Сохранение входящих сообщений"""
    try:
        chat_id, message_id, sender_id = event.chat_id, event.message.id, event.sender_id
        
        if OWNER_ID and sender_id == OWNER_ID:
            return
        
        if is_user_muted_new(sender_id):
            print(f'🔇 Глобально заглушенный {sender_id} - удаляем MSG {message_id}')
            try:
                await client.delete_messages(chat_id, message_id)
                print(f'✅ Удалено!')
            except Exception as e:
                print(f'⚠️ Ошибка удаления: {e}')
            return
        
        is_private, is_group = event.is_private, event.is_group
        if not should_save_message(chat_id, is_private, is_group):
            return
        
        sender = await event.get_sender()
        is_bot = getattr(sender, 'bot', False)
        
        config = load_saver_config()
        if is_bot and not config.get('save_bots', False):
            return
        
        sender_name = getattr(sender, 'first_name', 'Неизвестно')
        if hasattr(sender, 'username') and sender.username:
            sender_name += f' (@{sender.username})'
        
        is_ttl_media = False
        if hasattr(event.message, 'media'):
            if hasattr(event.message.media, 'photo') and event.message.media.photo:
                if hasattr(event.message.media, 'ttl_seconds') and event.message.media.ttl_seconds:
                    is_ttl_media = True
            elif hasattr(event.message.media, 'document') and event.message.media.document:
                if hasattr(event.message.media, 'ttl_seconds') and event.message.media.ttl_seconds:
                    is_ttl_media = True
        
        save_this_media = config.get('save_media', True)
        if is_ttl_media and config.get('save_ttl_media', False):
            save_this_media = True
        
        message_data = {
            'chat_id': chat_id,
            'message_id': message_id,
            'sender_id': sender_id,
            'sender_name': sender_name,
            'is_bot': is_bot,
            'text': event.message.message or '',
            'date': event.message.date.isoformat() if event.message.date else None,
            'has_photo': bool(event.message.photo),
            'has_video': bool(event.message.video),
            'has_document': bool(event.message.document),
            'has_voice': bool(event.message.voice),
            'is_ttl': is_ttl_media,
            'media_path': None
        }
        
        if save_this_media and (event.message.photo or event.message.video or 
                                event.message.document or event.message.voice or is_ttl_media):
            message_data['media_path'] = await save_media_file(event.message)
        
        store_message_immediately(chat_id, message_data)
    except Exception as e:
        print(f'❌ Ошибка сохранения: {e}')

@client.on(events.MessageDeleted)
async def deleted_message_handler(event):
    """Обработка удаленных сообщений"""
    try:
        chat_id, deleted_ids = event.chat_id, event.deleted_ids
        print(f'🗑️ Удалено {len(deleted_ids)} сообщений')
        for message_id in deleted_ids:
            message_data = get_stored_message(chat_id, message_id)
            if message_data:
                real_chat_id = message_data.get('chat_id')
                message_data['deleted_at'] = (datetime.now() + timedelta(hours=3)).isoformat()
                
                config = load_saver_config()
                should_forward = False
                caption_prefix = ""
                media_path = message_data.get('media_path')
                
                if message_data.get('has_photo') and config.get('save_media', True):
                    should_forward = True
                    caption_prefix = "🖼️ Удалённое фото"
                elif message_data.get('has_video') and config.get('save_media', True):
                    should_forward = True
                    caption_prefix = "🎥 Удалённое видео"
                elif message_data.get('has_voice') and config.get('save_voice', True):
                    should_forward = True
                    caption_prefix = "🎤 Удалённое ГС"
                elif message_data.get('is_ttl') and config.get('save_ttl_media', False):
                    should_forward = True
                    caption_prefix = "⏱️ Скоротечное медиа"
                
                if should_forward and media_path:
                    sender_name = message_data.get('sender_name', 'Неизвестно')
                    msg_text = message_data.get('text', '')
                    full_caption = f"{caption_prefix}\n👤 От: {sender_name}\n🗑️ Удалено: {message_data.get('deleted_at', '')[:16]}"
                    if msg_text:
                        full_caption += f"\n📝 Текст: {msg_text[:100]}"
                    
                    await forward_to_saved(media_path, full_caption)
                
                add_deleted_message(real_chat_id, message_data)
    except Exception as e:
        print(f'❌ Ошибка обработки удаленного: {e}')

@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    """Обработка входящих сообщений для ИИ"""
    try:
        chat_id = event.chat_id
        sender_id = event.sender_id
        
        if sender_id == OWNER_ID:
            return
        
        if is_user_muted_new(sender_id):
            return

        if BOT_ID and sender_id == BOT_ID:
            return
        
        config = load_ai_config()
        
        if not config.get('enabled', False):
            return
        
        schedule = config.get('schedule', {'start': 0, 'end': 0})
        if schedule['start'] != schedule['end']:
            current_hour = (datetime.now() + timedelta(hours=3)).hour
            
            is_in_schedule = False
            if schedule['start'] < schedule['end']:
                if schedule['start'] <= current_hour < schedule['end']:
                    is_in_schedule = True
            else:
                if current_hour >= schedule['start'] or current_hour < schedule['end']:
                    is_in_schedule = True
            
            if not is_in_schedule:
                return

        advanced = config.get('advanced', {})
        is_private = event.is_private
        is_group = event.is_group
        
        allowed = False
        if advanced.get('auto_reply_all', False):
            allowed = True
        
        if is_private and config.get('ai_private_enabled', False):
            allowed = True
        if is_group and config.get('ai_groups_enabled', False):
            allowed = True
        
        if is_chat_active(chat_id):
            allowed = True
        
        bio_sent = False
        if is_private:
            about_config = load_about_config()
            if about_config.get('enabled'):
                seen = about_config.get('seen_users', [])
                if sender_id not in seen:
                    print(f"👋 sending bio to {sender_id}")
                    await send_bio_message(event)
                    
                    seen.append(sender_id)
                    about_config['seen_users'] = seen
                    save_about_config(about_config)
                    bio_sent = True
        
        if bio_sent:
            return
        
        if not allowed:
            return
        
        message_text = event.message.message or ''
        
        if is_command_message(message_text):
            return
        
        if event.message.voice:
            advanced = config.get('advanced', {})
            if advanced.get('voice_enabled', True):
                voice_path = await save_media_file(event.message)
                if voice_path:
                    transcription = await transcribe_voice(voice_path)
                    message_text = f"[голосовое: {transcription}]"

        if hasattr(event.message, 'video_note') and event.message.video_note:
            advanced = config.get('advanced', {})
            if advanced.get('voice_enabled', True):
                video_note_path = await save_media_file(event.message)
                if video_note_path:
                    transcription = await transcribe_voice(video_note_path)
                    message_text = f"[видеосообщение: {transcription}]"
        
        if event.message.photo:
            advanced = config.get('advanced', {})
            if advanced.get('photo_enabled', True):
                photo_path = await save_media_file(event.message)
                if photo_path:
                    description = await describe_photo(photo_path)
                    if message_text:
                        message_text = f"{message_text} [фото: {description}]"
                    else:
                        message_text = f"[фото: {description}]"
        
        if not message_text:
            return
        
        save_message(chat_id, 'user', message_text)
        
        history = get_chat_history(chat_id)
        
        response_content = await get_ai_response(history, config)
        
        if response_content and 'ошибка' not in response_content.lower():
            save_message(chat_id, 'assistant', response_content)
            await event.respond(response_content)
    except RPCError as e:
        if 'TOPIC_CLOSED' in str(e) or 'CHAT_WRITE_FORBIDDEN' in str(e):
            pass
    except Exception as e:
        print(f'❌ Ошибка входящего: {e}')

@client.on(events.NewMessage(outgoing=True))
async def outgoing_handler(event):
    """Обработка исходящих сообщений"""
    try:
        chat_id = event.chat_id
        message_text = event.message.message or ''
        
        # Проверка на загрузку конфига из JSON файла
        if event.message.document and chat_id == OWNER_ID:
            filename = ''
            if hasattr(event.message.document, 'attributes'):
                for attr in event.message.document.attributes:
                    if hasattr(attr, 'file_name'):
                        filename = attr.file_name
                        break
            
            if filename.endswith('.json'):
                file_path = await save_media_file(event.message)
                if file_path:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            new_config = json.load(f)
                        
                        save_ai_config(new_config)
                        
                        msg = await event.respond('✅ Конфигурация загружена из файла!')
                        await event.delete()
                        await register_command_message(chat_id, msg.id)
                        return
                    except Exception as e:
                        msg = await event.respond(f'❌ Ошибка загрузки конфига: {e}')
                        await event.delete()
                        await register_command_message(chat_id, msg.id)
                        return
        
        # Команда удаления последнего меню
        if message_text.lower() == '.del':
            await delete_previous_command(chat_id)
            await event.delete()
            return
        
        # Команда .bio
        if message_text.lower() == '.bio':
            await delete_previous_command(chat_id)
            try:
                await event.delete()
            except:
                pass
            if not await send_bio_message(event):
                msg = await event.respond('❌ Bio выключено или не настроено!')
                await asyncio.sleep(2)
                try:
                    await msg.delete()
                except:
                    pass
            return
        
        # Проверяем выбор цифрой
        if await handle_digit_selection(event, message_text):
            return
        
        # Команды ИИ конфига
        if message_text.lower().startswith('.aiconfig'):
            if await handle_aiconfig_commands(event, message_text):
                return
        
        # Команды заглушки
        if message_text.lower().startswith('.замолчи') or message_text.lower().startswith('.говори') or message_text.lower() == '.список':
            if await handle_mute_commands_new(event, message_text):
                return
        
        if message_text.lower().startswith('.saver'):
            if await handle_saver_commands(event, message_text):
                return
        
        if message_text.lower().startswith('.anim'):
            if await handle_animation_commands(event, message_text):
                return
        
        # Команда быстрого запроса к ИИ
        if message_text.lower().startswith('.neiro '):
            if await handle_neiro_command(event, message_text):
                return
        
        # Команды управления ИИ в чате
        if message_text.lower() == '.aistop':
            await delete_previous_command(chat_id)
            config = load_ai_config()
            
            if 'advanced' not in config:
                config['advanced'] = {}
            config['advanced']['auto_reply_all'] = False
            save_ai_config(config)
            
            msg = await event.respond('❌ ИИ авто-ответ выключен глобально!\n\n💡 Включить: `.aiconfig auto on`')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return
        
        if message_text.lower() == '.aiclear':
            await delete_previous_command(chat_id)
            clear_chat_history(chat_id)
            msg = await event.respond('🗑️ История очищена!')
            await event.delete()
            await register_command_message(chat_id, msg.id)
            return
        
        # Автоматическая анимация
        settings = get_animation_settings(chat_id)
        if settings['mode'] and message_text.strip():
            if not message_text.startswith('.'):
                await run_animation(event.message, message_text, settings['mode'], settings['duration'], settings['interval'], settings.get('font'))
                return
    except Exception as e:
        print(f'❌ Ошибка исходящего: {e}')

# ============ ГЛАВНАЯ ФУНКЦИЯ ============
async def main():
    global OWNER_ID, BOT_ID
    print('🚀 Запуск Telegram Userbot...')
    print(f'📝 Сессия: {SESSION_NAME}.session')
    
    Path(MEDIA_FOLDER).mkdir(parents=True, exist_ok=True)
    
    if not os.path.exists(f'{SESSION_NAME}.session'):
        print(f'❌ Файл сессии не найден!')
        sys.exit(1)
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print('❌ Сессия не авторизована!')
            sys.exit(1)
        
        me = await client.get_me()
        OWNER_ID = me.id
        
        print(f'✅ Userbot запущен!')
        print(f'👤 Аккаунт: {me.username or me.first_name} (ID: {OWNER_ID})')
        print(f'🤖 AI: {MODEL_NAME}')
        print(f'🔗 API: OnlySQ')
        print(f'\n🆕 ПОЛНАЯ ВЕРСИЯ:')
        print('✅ Настройка сохранения сообщений ботов')
        print('✅ Все команды очистки работают')
        print('✅ Полный функционал в боте')
        print('✅ Bio с выбором позиции аудио')
        print('✅ 6 шрифтов в анимациях')
        print('✅ Команда .bio автоудаляется')
        print('✅ 3000+ строк кода')
        print('\n📝 КОМАНДЫ:')
        print('   /start (боту) - 🎮 Панель управления')
        print('   .bio - 👋 Отправить био')
        print('   .anim <тип> <шрифт> <текст> - 🎬 Анимация')
        print('   .neiro <запрос> - ⚡ Быстрый AI')
        print('   .aiconfig help - 🤖 Помощь по AI')
        print('   .saver help - 💾 Помощь по Saver')
        print('\n🎧 Слушаю...\n')
        
        if not BOT_TOKEN or BOT_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            print('\n⚠️ ВНИМАНИЕ: BOT_TOKEN не указан!')
            await client.run_until_disconnected()
        else:
            print(f'🤖 Запуск управляющего бота...')
            try:
                await bot.start(bot_token=BOT_TOKEN)
                bot_me = await bot.get_me()
                BOT_ID = bot_me.id
                print(f'✅ Бот запущен: @{bot_me.username} (ID: {BOT_ID})')
                print(f'   Напишите /start в ЛС боту.')
                
                await asyncio.gather(
                    client.run_until_disconnected(),
                    bot.run_until_disconnected()
                )
            except Exception as e:
                print(f'❌ Ошибка запуска бота: {e}')
                await client.run_until_disconnected()
            
    except Exception as e:
        print(f'❌ Ошибка: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n👋 Userbot остановлен')
        try:
            with open(TEMP_SELECTION_FILE, 'w', encoding='utf-8') as f:
                json.dump(user_selection_state, f, default=str, ensure_ascii=False, indent=2)
        except:
            pass
    except Exception as e:
        print(f'\n❌ Критическая ошибка: {e}')
        import traceback
        traceback.print_exc()
        sys.exit(1)
