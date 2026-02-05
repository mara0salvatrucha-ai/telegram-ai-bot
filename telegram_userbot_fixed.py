"""
TELEGRAM USERBOT - MULTI-ACCOUNT VERSION
=========================================
Поддержка 3 аккаунтов Telegram с единым управлением ИИ

ИНСТРУКЦИЯ ПО УСТАНОВКЕ:
------------------------
1. Получите API_ID и API_HASH на https://my.telegram.org/apps
2. Создайте 3 сессии для каждого аккаунта (см. раздел НАСТРОЙКА АККАУНТОВ)
3. Настройте переменные окружения или отредактируйте секцию КОНФИГУРАЦИЯ
4. Запустите: python telegram_multibot.py

ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ:
--------------------
# Аккаунт 1
API_ID_1=ваш_api_id
API_HASH_1=ваш_api_hash
PHONE_1=+79001234567
SESSION_1=session_account1

# Аккаунт 2
API_ID_2=ваш_api_id
API_HASH_2=ваш_api_hash
PHONE_2=+79001234568
SESSION_2=session_account2

# Аккаунт 3
API_ID_3=ваш_api_id
API_HASH_3=ваш_api_hash
PHONE_3=+79001234569
SESSION_3=session_account3

# Общие
OPENAI_API_KEY=ваш_ключ_api
"""

import asyncio
import json
import os
import sys
import base64
import ssl
from datetime import datetime, timedelta
from pathlib import Path
import aiohttp
from telethon import TelegramClient, events
from telethon.errors import RPCError
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, InputPeerSelf

# ============ КОНФИГУРАЦИЯ АККАУНТОВ ============
# Можно редактировать напрямую или использовать переменные окружения

ACCOUNTS = [
    {
        'name': 'Account1',
        'api_id': int(os.environ.get('API_ID_1', '30612474')),
        'api_hash': os.environ.get('API_HASH_1', 'e602dd5243cfe4ea3c165c2b3d49a810'),
        'phone': os.environ.get('PHONE_1', '+79786180647'),
        'session': os.environ.get('SESSION_1', 'session_account1'),
    },
    {
        'name': 'Account2',
        'api_id': int(os.environ.get('API_ID_2', '39678712')),
        'api_hash': os.environ.get('API_HASH_2', '3089ac53d532e75deb5dd641e4863d49'),
        'phone': os.environ.get('PHONE_2', '+919036205120'),
        'session': os.environ.get('SESSION_2', 'session_account2'),
    },
    {
        'name': 'Account3',
        'api_id': int(os.environ.get('API_ID_3', '')),
        'api_hash': os.environ.get('API_HASH_3', ''),
        'phone': os.environ.get('PHONE_3', ''),
        'session': os.environ.get('SESSION_3', 'session_account3'),
    },
]

# OnlySQ API
AI_API_URL = 'https://api.onlysq.ru/ai/openai/chat/completions'
AI_API_KEY = os.environ.get('OPENAI_API_KEY', 'openai')
MODEL_NAME = 'gpt-4o-mini'

# Файлы БД (будут с префиксом аккаунта)
MEDIA_FOLDER = 'saved_media'

# Глобальные переменные
COMMAND_PREFIXES = ['.saver', '.deleted', '.aiconfig', '.aistop', '.aiston', '.aichat', '.aiclear', '.anim', '.замолчи', '.говори', '.del', '.список', '.neiro']

# ============ КЛАСС ДЛЯ КАЖДОГО АККАУНТА ============
class UserBot:
    def __init__(self, account_config, account_index):
        self.name = account_config['name']
        self.api_id = account_config['api_id']
        self.api_hash = account_config['api_hash']
        self.phone = account_config['phone']
        self.session = account_config['session']
        self.index = account_index
        
        # Файлы с префиксом аккаунта
        self.prefix = f'acc{account_index}_'
        self.DB_FILE = f'{self.prefix}messages.json'
        self.ACTIVE_CHATS_FILE = f'{self.prefix}active_chats.json'
        self.DELETED_MESSAGES_DB = f'{self.prefix}deleted_messages.json'
        self.SAVER_CONFIG_FILE = f'{self.prefix}saver_config.json'
        self.MESSAGES_STORAGE_DB = f'{self.prefix}messages_storage.json'
        self.ANIMATION_CONFIG_FILE = f'{self.prefix}animation_config.json'
        self.MUTE_CONFIG_FILE = f'{self.prefix}mute_config.json'
        self.AI_CONFIG_FILE = f'{self.prefix}ai_config.json'
        self.MUTED_USERS_DB = f'{self.prefix}muted_users_db.json'
        self.AI_CHAT_CONFIG_FILE = f'{self.prefix}ai_chat_config.json'  # НОВОЕ: конфиг по чатам
        
        self.client = TelegramClient(self.session, self.api_id, self.api_hash)
        self.owner_id = None
        self.db = {}
        self.last_command_message = {}
        self.user_selection_state = {}
        
    # ============ ФУНКЦИИ БД ============
    def load_db(self):
        if os.path.exists(self.DB_FILE):
            try:
                with open(self.DB_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_db(self, data):
        try:
            with open(self.DB_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def load_ai_config(self):
        """Загрузка конфигурации ИИ"""
        if os.path.exists(self.AI_CONFIG_FILE):
            try:
                with open(self.AI_CONFIG_FILE, 'r', encoding='utf-8') as f:
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
    
    def save_ai_config(self, config):
        try:
            with open(self.AI_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    # ============ НОВОЕ: КОНФИГУРАЦИЯ ИИ ПО ЧАТАМ ============
    def load_ai_chat_config(self):
        """Загрузка конфигурации ИИ по чатам"""
        if os.path.exists(self.AI_CHAT_CONFIG_FILE):
            try:
                with open(self.AI_CHAT_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'disabled_chats': [],      # Чаты где ИИ выключен
            'enabled_chats': [],       # Чаты где ИИ включен принудительно
            'disabled_groups': False,  # Выключить во всех группах
            'disabled_private': False, # Выключить во всех личных
        }
    
    def save_ai_chat_config(self, config):
        try:
            with open(self.AI_CHAT_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def is_ai_enabled_for_chat(self, chat_id, is_private, is_group):
        """Проверка включен ли ИИ для конкретного чата"""
        config = self.load_ai_config()
        chat_config = self.load_ai_chat_config()
        
        # Если глобально выключен - сразу нет
        if not config.get('enabled', False):
            return False
        
        chat_id_str = str(chat_id)
        
        # Проверка на принудительное включение
        if chat_id_str in chat_config.get('enabled_chats', []):
            return True
        
        # Проверка на принудительное выключение
        if chat_id_str in chat_config.get('disabled_chats', []):
            return False
        
        # Проверка глобальных настроек по типу чата
        if is_group and chat_config.get('disabled_groups', False):
            return False
        
        if is_private and chat_config.get('disabled_private', False):
            return False
        
        return True
    
    def disable_ai_in_chat(self, chat_id):
        """Выключить ИИ в чате"""
        config = self.load_ai_chat_config()
        chat_id_str = str(chat_id)
        
        if chat_id_str not in config['disabled_chats']:
            config['disabled_chats'].append(chat_id_str)
        
        if chat_id_str in config.get('enabled_chats', []):
            config['enabled_chats'].remove(chat_id_str)
        
        self.save_ai_chat_config(config)
    
    def enable_ai_in_chat(self, chat_id):
        """Включить ИИ в чате"""
        config = self.load_ai_chat_config()
        chat_id_str = str(chat_id)
        
        if chat_id_str in config.get('disabled_chats', []):
            config['disabled_chats'].remove(chat_id_str)
        
        if chat_id_str not in config.get('enabled_chats', []):
            if 'enabled_chats' not in config:
                config['enabled_chats'] = []
            config['enabled_chats'].append(chat_id_str)
        
        self.save_ai_chat_config(config)
    
    def load_muted_users_db(self):
        if os.path.exists(self.MUTED_USERS_DB):
            try:
                with open(self.MUTED_USERS_DB, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_muted_users_db(self, data):
        try:
            with open(self.MUTED_USERS_DB, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def mute_user_new(self, user_id, user_name, chat_id=None):
        db = self.load_muted_users_db()
        user_key = str(user_id)
        db[user_key] = {
            'user_name': user_name,
            'user_id': user_id,
            'muted_at': datetime.now().isoformat(),
            'chat_id': chat_id
        }
        self.save_muted_users_db(db)
    
    def unmute_user_new(self, user_id):
        db = self.load_muted_users_db()
        user_key = str(user_id)
        if user_key in db:
            user_info = db.pop(user_key)
            self.save_muted_users_db(db)
            return user_info
        return None
    
    def is_user_muted_new(self, user_id):
        db = self.load_muted_users_db()
        return str(user_id) in db
    
    def get_all_muted_users(self):
        return self.load_muted_users_db()
    
    def load_saver_config(self):
        if os.path.exists(self.SAVER_CONFIG_FILE):
            try:
                with open(self.SAVER_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if 'save_text' not in config:
                        config['save_text'] = True
                    if 'save_voice' not in config:
                        config['save_voice'] = True
                    if 'save_ttl_media' not in config:
                        config['save_ttl_media'] = False
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
            'save_ttl_media': False
        }
    
    def save_saver_config(self, config):
        try:
            with open(self.SAVER_CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    def should_save_message(self, chat_id, is_private, is_group):
        config = self.load_saver_config()
        chat_id_str = str(chat_id)
        if is_private and config['save_private']:
            return True
        if is_group and config['save_groups']:
            return True
        if chat_id_str in config['save_channels']:
            return True
        return False
    
    def is_command_message(self, text):
        if not text:
            return False
        text_lower = text.lower().strip()
        return any(text_lower.startswith(prefix.lower()) for prefix in COMMAND_PREFIXES)
    
    async def delete_previous_command(self, chat_id):
        if chat_id in self.last_command_message:
            try:
                msg_ids = self.last_command_message[chat_id]
                await self.client.delete_messages(chat_id, msg_ids if isinstance(msg_ids, list) else [msg_ids])
            except:
                pass
    
    async def register_command_message(self, chat_id, message_id):
        self.last_command_message[chat_id] = message_id
    
    async def save_media_file(self, message, media_folder=MEDIA_FOLDER):
        try:
            Path(media_folder).mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            chat_id, msg_id = message.chat_id, message.id
            
            if message.photo:
                ext, mtype = 'jpg', 'photo'
            elif message.video:
                ext, mtype = 'mp4', 'video'
            elif message.voice:
                ext, mtype = 'ogg', 'voice'
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
            print(f'[{self.name}] 💾 Сохранен: {filename}')
            return filepath
        except Exception as e:
            print(f'[{self.name}] ⚠️ Ошибка сохранения медиа: {e}')
            return None
    
    # ============ ФУНКЦИИ ИИ ============
    async def get_ai_response(self, messages, config=None):
        try:
            if config is None:
                config = self.load_ai_config()
            
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
                        print(f'[{self.name}] ❌ API ошибка {resp.status}: {error_text}')
                        return 'не смог ответить'
        except Exception as e:
            print(f'[{self.name}] ❌ API ошибка: {e}')
            return 'ошибка апи'
    
    def get_chat_history(self, chat_id, limit=10):
        config = self.load_ai_config()
        advanced = config.get('advanced', {})
        max_history = advanced.get('max_history', 20)
        limit = min(limit, max_history)
        
        chat_key = str(chat_id)
        if chat_key not in self.db:
            self.db[chat_key] = []
        
        filtered = [msg for msg in self.db[chat_key] if not (msg.get('role') == 'assistant' and 'ошибка' in msg.get('content', '').lower())]
        return filtered[-limit:]
    
    def save_message(self, chat_id, role, content):
        chat_key = str(chat_id)
        if chat_key not in self.db:
            self.db[chat_key] = []
        
        if role == 'assistant' and 'ошибка' in content.lower():
            return
        
        message = {'role': role, 'content': content}
        self.db[chat_key].append(message)
        
        config = self.load_ai_config()
        advanced = config.get('advanced', {})
        max_history = advanced.get('max_history', 20)
        
        if len(self.db[chat_key]) > max_history * 2:
            self.db[chat_key] = self.db[chat_key][-max_history * 2:]
        
        self.save_db(self.db)
    
    def clear_chat_history(self, chat_id):
        chat_key = str(chat_id)
        if chat_key in self.db:
            self.db[chat_key] = []
            self.save_db(self.db)
    
    # ============ ОБРАБОТЧИКИ КОМАНД ============
    async def handle_aiconfig_commands(self, event, message_text):
        chat_id = event.chat_id
        message_text = message_text.strip()
        
        await self.delete_previous_command(chat_id)
        
        # Справка
        if message_text.lower() == '.aiconfig help':
            help_text = f'''🤖 **ПАНЕЛЬ УПРАВЛЕНИЯ ИИ** [{self.name}]

📋 **ОСНОВНЫЕ**
┣‣ `.aiconfig status` - 📊 Статус
┣‣ `.aiconfig on` - ✅ Включить ИИ
┣‣ `.aiconfig off` - ❌ Выключить ИИ

⚙️ **АВТО-ОТВЕТ**
┣‣ `.aiconfig auto on` - 🤖 Авто-ответ всем
┣‣ `.aiconfig auto off` - ❌ Выключить авто

🎯 **УПРАВЛЕНИЕ ПО ЧАТАМ**
┣‣ `.aistop` - ❌ Выключить ИИ **здесь**
┣‣ `.aiston` - ✅ Включить ИИ **здесь**
┣‣ `.aichat status` - 📊 Статус по чатам
┣‣ `.aichat groups off` - Выкл во всех группах
┣‣ `.aichat groups on` - Вкл в группах
┣‣ `.aichat private off` - Выкл в личных
┣‣ `.aichat private on` - Вкл в личных

💾 **КОНФИГУРАЦИЯ**
┣‣ `.aiconfig show` - Показать конфиг
┣‣ `.aiconfig export` - Экспорт JSON
┣‣ `.aiconfig reset` - Сброс

📝 **ДРУГОЕ**
┣‣ `.aiconfig personality <текст>` - Личность
┣‣ `.aiclear` - Очистить историю
┣‣ `.neiro <запрос>` - Быстрый запрос

🌐 API: OnlySQ | Модель: {MODEL_NAME}'''
            
            msg = await event.respond(help_text)
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        # Статус
        if message_text.lower() == '.aiconfig status':
            config = self.load_ai_config()
            chat_config = self.load_ai_chat_config()
            advanced = config.get('advanced', {})
            
            status_text = f'''🤖 **СТАТУС ИИ** [{self.name}]

🔌 Глобально: {"✅ ВКЛ" if config.get('enabled', False) else "❌ ВЫКЛ"}
🤖 Авто-ответ: {"✅" if advanced.get('auto_reply_all', False) else "❌"}

**ПО ЧАТАМ:**
👥 Группы: {"❌ ВЫКЛ" if chat_config.get('disabled_groups', False) else "✅ ВКЛ"}
💬 Личные: {"❌ ВЫКЛ" if chat_config.get('disabled_private', False) else "✅ ВКЛ"}
🚫 Исключения: {len(chat_config.get('disabled_chats', []))} чатов

**НАСТРОЙКИ:**
🔡 Маленькие буквы: {"✅" if advanced.get('lowercase', True) else "❌"}
📊 История: {advanced.get('max_history', 20)}
🌡️ Temperature: {advanced.get('temperature', 0.7)}

🧠 Личность: {config.get('personality', '')[:60]}...'''
            
            msg = await event.respond(status_text)
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        # Включить/Выключить глобально
        if message_text.lower() == '.aiconfig on':
            config = self.load_ai_config()
            config['enabled'] = True
            self.save_ai_config(config)
            msg = await event.respond(f'✅ ИИ включен глобально [{self.name}]')
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        if message_text.lower() == '.aiconfig off':
            config = self.load_ai_config()
            config['enabled'] = False
            self.save_ai_config(config)
            msg = await event.respond(f'❌ ИИ выключен глобально [{self.name}]')
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        # Авто-ответ
        if message_text.lower() == '.aiconfig auto on':
            config = self.load_ai_config()
            if 'advanced' not in config:
                config['advanced'] = {}
            config['advanced']['auto_reply_all'] = True
            self.save_ai_config(config)
            msg = await event.respond(f'✅ Авто-ответ включен [{self.name}]')
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        if message_text.lower() == '.aiconfig auto off':
            config = self.load_ai_config()
            if 'advanced' not in config:
                config['advanced'] = {}
            config['advanced']['auto_reply_all'] = False
            self.save_ai_config(config)
            msg = await event.respond(f'❌ Авто-ответ выключен [{self.name}]')
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        # Показать конфиг
        if message_text.lower() == '.aiconfig show':
            config = self.load_ai_config()
            config_text = json.dumps(config, ensure_ascii=False, indent=2)
            msg = await event.respond(f'```json\n{config_text}\n```')
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        # Экспорт
        if message_text.lower() == '.aiconfig export':
            config = self.load_ai_config()
            config_text = json.dumps(config, ensure_ascii=False, indent=2)
            
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json', delete=False) as f:
                f.write(config_text)
                temp_path = f.name
            
            try:
                await self.client.send_file(chat_id, temp_path, caption=f'📤 Конфиг ИИ [{self.name}]')
                await event.delete()
                os.unlink(temp_path)
            except:
                os.unlink(temp_path)
            return True
        
        # Сброс
        if message_text.lower() == '.aiconfig reset':
            default_config = {
                'enabled': False,
                'personality': 'отвечай как обычный человек, кратко и по делу. пиши с маленькой буквы'
            }
            self.save_ai_config(default_config)
            msg = await event.respond(f'🔄 Конфиг сброшен [{self.name}]')
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        # Личность
        if message_text.lower().startswith('.aiconfig personality '):
            personality = message_text[len('.aiconfig personality '):].strip()
            if personality:
                config = self.load_ai_config()
                config['personality'] = personality
                self.save_ai_config(config)
                msg = await event.respond(f'✅ Личность обновлена:\n{personality[:200]}')
            else:
                msg = await event.respond('❌ Укажите текст личности')
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        return False
    
    async def handle_aichat_commands(self, event, message_text):
        """Команды управления ИИ по чатам"""
        chat_id = event.chat_id
        message_text = message_text.strip()
        
        await self.delete_previous_command(chat_id)
        
        # Статус по чатам
        if message_text.lower() == '.aichat status':
            chat_config = self.load_ai_chat_config()
            
            status_text = f'''📊 **ИИ ПО ЧАТАМ** [{self.name}]

👥 Группы: {"❌ ВЫКЛ глобально" if chat_config.get('disabled_groups', False) else "✅ ВКЛ"}
💬 Личные: {"❌ ВЫКЛ глобально" if chat_config.get('disabled_private', False) else "✅ ВКЛ"}

**Исключения:**
🚫 Выключен в: {len(chat_config.get('disabled_chats', []))} чатах
✅ Принудительно вкл: {len(chat_config.get('enabled_chats', []))} чатах

📍 Этот чат (ID: `{chat_id}`):
{"🚫 ИИ ВЫКЛЮЧЕН" if str(chat_id) in chat_config.get('disabled_chats', []) else "✅ ИИ ВКЛЮЧЕН"}

**Команды:**
• `.aistop` - выключить здесь
• `.aiston` - включить здесь
• `.aichat groups off/on`
• `.aichat private off/on`'''
            
            msg = await event.respond(status_text)
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        # Группы вкл/выкл
        if message_text.lower() == '.aichat groups off':
            config = self.load_ai_chat_config()
            config['disabled_groups'] = True
            self.save_ai_chat_config(config)
            msg = await event.respond(f'❌ ИИ выключен во ВСЕХ группах [{self.name}]')
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        if message_text.lower() == '.aichat groups on':
            config = self.load_ai_chat_config()
            config['disabled_groups'] = False
            self.save_ai_chat_config(config)
            msg = await event.respond(f'✅ ИИ включен в группах [{self.name}]')
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        # Личные вкл/выкл
        if message_text.lower() == '.aichat private off':
            config = self.load_ai_chat_config()
            config['disabled_private'] = True
            self.save_ai_chat_config(config)
            msg = await event.respond(f'❌ ИИ выключен в личных чатах [{self.name}]')
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        if message_text.lower() == '.aichat private on':
            config = self.load_ai_chat_config()
            config['disabled_private'] = False
            self.save_ai_chat_config(config)
            msg = await event.respond(f'✅ ИИ включен в личных чатах [{self.name}]')
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        return False
    
    async def handle_mute_commands_new(self, event, message_text):
        """Обработка команд заглушки/разглушки"""
        chat_id = event.chat_id
        message_text = message_text.strip()
        
        await self.delete_previous_command(chat_id)
        
        if message_text.lower() == '.список':
            muted = self.get_all_muted_users()
            if not muted:
                msg = await event.respond(f'📭 Нет заглушенных [{self.name}]')
            else:
                list_text = f'🔇 **ЗАГЛУШЕННЫЕ ({len(muted)})** [{self.name}]:\n\n'
                for i, (user_id, info) in enumerate(muted.items(), 1):
                    list_text += f'{i}. {info.get("user_name", "?")} (ID: `{user_id}`)\n'
                msg = await event.respond(list_text)
            
            await event.delete()
            await self.register_command_message(chat_id, msg.id)
            return True
        
        if message_text.lower() == '.замолчи':
            if event.reply_to_msg_id:
                try:
                    reply_msg = await event.get_reply_message()
                    user_id = reply_msg.sender_id
                    
                    if user_id == self.owner_id:
                        msg = await event.respond('❌ Нельзя заглушить себя!')
                        await event.delete()
                        await self.register_command_message(chat_id, msg.id)
                        return True
                    
                    sender = await reply_msg.get_sender()
                    user_name = getattr(sender, 'first_name', 'Неизвестно')
                    if hasattr(sender, 'username') and sender.username:
                        user_name += f' (@{sender.username})'
                    
                    self.mute_user_new(user_id, user_name, chat_id)
                    msg = await event.respond(f'🔇 **{user_name}** заглушен [{self.name}]')
                    await event.delete()
                    await self.register_command_message(chat_id, msg.id)
                    return True
                except Exception as e:
                    msg = await event.respond(f'❌ Ошибка: {e}')
                    await event.delete()
                    await self.register_command_message(chat_id, msg.id)
                    return True
            else:
                msg = await event.respond('❌ Ответьте на сообщение командой `.замолчи`')
                await event.delete()
                await self.register_command_message(chat_id, msg.id)
                return True
        
        if message_text.lower().startswith('.говори'):
            if event.reply_to_msg_id:
                try:
                    reply_msg = await event.get_reply_message()
                    user_id = reply_msg.sender_id
                    user_info = self.unmute_user_new(user_id)
                    
                    if user_info:
                        msg = await event.respond(f'🔊 **{user_info.get("user_name")}** разглушен [{self.name}]')
                    else:
                        msg = await event.respond('⚠️ Не был заглушен')
                    
                    await event.delete()
                    await self.register_command_message(chat_id, msg.id)
                    return True
                except Exception as e:
                    msg = await event.respond(f'❌ Ошибка: {e}')
                    await event.delete()
                    await self.register_command_message(chat_id, msg.id)
                    return True
            
            parts = message_text.split()
            if len(parts) >= 2:
                try:
                    user_id = int(parts[1])
                    user_info = self.unmute_user_new(user_id)
                    
                    if user_info:
                        msg = await event.respond(f'🔊 **{user_info.get("user_name")}** разглушен')
                    else:
                        msg = await event.respond(f'⚠️ Пользователь {user_id} не заглушен')
                    
                    await event.delete()
                    await self.register_command_message(chat_id, msg.id)
                    return True
                except ValueError:
                    msg = await event.respond('❌ Неверный ID')
                    await event.delete()
                    await self.register_command_message(chat_id, msg.id)
                    return True
            else:
                msg = await event.respond('❌ Используйте: `.говори <ID>` или ответом')
                await event.delete()
                await self.register_command_message(chat_id, msg.id)
                return True
        
        return False
    
    async def handle_neiro_command(self, event, message_text):
        """Быстрый запрос к ИИ"""
        try:
            if not message_text.lower().startswith('.neiro '):
                return False
            
            query = message_text[7:].strip()
            if not query:
                await event.edit('❌ Укажите запрос')
                return True
            
            await event.edit(f'🤖 **Запрос:** {query}\n\n⏳ Думаю...')
            
            messages = [{'role': 'user', 'content': query}]
            response = await self.get_ai_response(messages)
            
            await event.edit(f'🤖 **Запрос:** {query}\n\n📝 **Ответ:**\n```\n{response}\n```')
            return True
        except Exception as e:
            try:
                await event.edit(f'❌ Ошибка: {e}')
            except:
                pass
            return True
    
    # ============ НАСТРОЙКА ОБРАБОТЧИКОВ ============
    def setup_handlers(self):
        client = self.client
        
        @client.on(events.NewMessage(incoming=True))
        async def incoming_handler(event):
            try:
                chat_id = event.chat_id
                sender_id = event.sender_id
                
                if sender_id == self.owner_id:
                    return
                
                if self.is_user_muted_new(sender_id):
                    try:
                        await client.delete_messages(chat_id, event.message.id)
                    except:
                        pass
                    return
                
                config = self.load_ai_config()
                
                if not config.get('enabled', False):
                    return
                
                advanced = config.get('advanced', {})
                if not advanced.get('auto_reply_all', False):
                    return
                
                # Проверка по чатам
                if not self.is_ai_enabled_for_chat(chat_id, event.is_private, event.is_group):
                    return
                
                message_text = event.message.message or ''
                
                if self.is_command_message(message_text):
                    return
                
                if not message_text:
                    return
                
                self.save_message(chat_id, 'user', message_text)
                history = self.get_chat_history(chat_id)
                response = await self.get_ai_response(history, config)
                
                if response and 'ошибка' not in response.lower():
                    self.save_message(chat_id, 'assistant', response)
                    await event.respond(response)
            except Exception as e:
                print(f'[{self.name}] ❌ Ошибка входящего: {e}')
        
        @client.on(events.NewMessage(outgoing=True))
        async def outgoing_handler(event):
            try:
                chat_id = event.chat_id
                message_text = event.message.message or ''
                
                if message_text.lower() == '.del':
                    await self.delete_previous_command(chat_id)
                    await event.delete()
                    return
                
                # Команды ИИ
                if message_text.lower().startswith('.aiconfig'):
                    if await self.handle_aiconfig_commands(event, message_text):
                        return
                
                # Команды по чатам
                if message_text.lower().startswith('.aichat'):
                    if await self.handle_aichat_commands(event, message_text):
                        return
                
                # Быстрое выключение/включение в чате
                if message_text.lower() == '.aistop':
                    await self.delete_previous_command(chat_id)
                    self.disable_ai_in_chat(chat_id)
                    msg = await event.respond(f'❌ ИИ выключен в этом чате [{self.name}]\n\n💡 Включить: `.aiston`')
                    await event.delete()
                    await self.register_command_message(chat_id, msg.id)
                    return
                
                if message_text.lower() == '.aiston':
                    await self.delete_previous_command(chat_id)
                    self.enable_ai_in_chat(chat_id)
                    msg = await event.respond(f'✅ ИИ включен в этом чате [{self.name}]\n\n💡 Выключить: `.aistop`')
                    await event.delete()
                    await self.register_command_message(chat_id, msg.id)
                    return
                
                # Очистка истории
                if message_text.lower() == '.aiclear':
                    await self.delete_previous_command(chat_id)
                    self.clear_chat_history(chat_id)
                    msg = await event.respond('🗑️ История очищена')
                    await event.delete()
                    await self.register_command_message(chat_id, msg.id)
                    return
                
                # Заглушка
                if message_text.lower().startswith('.замолчи') or message_text.lower().startswith('.говори') or message_text.lower() == '.список':
                    if await self.handle_mute_commands_new(event, message_text):
                        return
                
                # Быстрый запрос
                if message_text.lower().startswith('.neiro '):
                    if await self.handle_neiro_command(event, message_text):
                        return
                        
            except Exception as e:
                print(f'[{self.name}] ❌ Ошибка исходящего: {e}')
    
    async def start(self):
        """Запуск бота"""
        print(f'🔄 [{self.name}] Запуск...')
        
        self.db = self.load_db()
        
        await self.client.connect()
        
        if not await self.client.is_user_authorized():
            print(f'⚠️ [{self.name}] Требуется авторизация!')
            print(f'   Телефон: {self.phone}')
            await self.client.send_code_request(self.phone)
            code = input(f'[{self.name}] Введите код из Telegram: ')
            try:
                await self.client.sign_in(self.phone, code)
            except Exception as e:
                if 'password' in str(e).lower():
                    password = input(f'[{self.name}] Введите пароль 2FA: ')
                    await self.client.sign_in(password=password)
                else:
                    raise e
        
        me = await self.client.get_me()
        self.owner_id = me.id
        
        self.setup_handlers()
        
        print(f'✅ [{self.name}] Запущен!')
        print(f'   👤 {me.username or me.first_name} (ID: {self.owner_id})')
        
        return self.client

# ============ ГЛАВНАЯ ФУНКЦИЯ ============
async def main():
    print('=' * 50)
    print('🚀 TELEGRAM MULTI-ACCOUNT USERBOT')
    print('=' * 50)
    print()
    
    Path(MEDIA_FOLDER).mkdir(parents=True, exist_ok=True)
    
    bots = []
    clients = []
    
    for i, account in enumerate(ACCOUNTS, 1):
        try:
            bot = UserBot(account, i)
            client = await bot.start()
            bots.append(bot)
            clients.append(client)
        except Exception as e:
            print(f'❌ Ошибка запуска аккаунта {i}: {e}')
    
    if not clients:
        print('❌ Ни один аккаунт не запущен!')
        return
    
    print()
    print('=' * 50)
    print(f'✅ Запущено аккаунтов: {len(clients)}/{len(ACCOUNTS)}')
    print('=' * 50)
    print()
    print('📝 КОМАНДЫ:')
    print('   .aiconfig help  - Справка по ИИ')
    print('   .aiconfig on    - Включить ИИ глобально')
    print('   .aiconfig off   - Выключить ИИ глобально')
    print('   .aistop         - Выключить ИИ в этом чате')
    print('   .aiston         - Включить ИИ в этом чате')
    print('   .aichat status  - Статус по чатам')
    print('   .neiro <текст>  - Быстрый запрос')
    print()
    print('🎧 Слушаю...')
    print()
    
    await asyncio.gather(*[c.run_until_disconnected() for c in clients])

# ============ ЗАПУСК ============
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n👋 Все боты остановлены')
    except Exception as e:
        print(f'\n❌ Критическая ошибка: {e}')
        import traceback
        traceback.print_exc()
