from enum import Enum


class NewsType(str, Enum):
    """Типы событий в ленте новостей"""
    
    FRIEND_COMMENT = "friend_comment"    # комментарий друга
    GAME_RECORD = "game_record"          # рекорд в игре
    NEW_CHIP = "new_chip"                # новый вкус
    NEW_FOLLOWER = "new_follower"        # на вас подписались
    ADMIN_POST = "admin_post"            # пост админа
    RUMOR = "rumor"                      # слухи
    POLL = "poll"                        # опрос
    
    # Запланированы:
    # FRIEND_PHOTO = "friend_photo"      # друг запостил фото
    # ACHIEVEMENT = "achievement"        # достижение