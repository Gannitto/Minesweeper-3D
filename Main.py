from itertools import product
from ursina import *
import random

from ursina import texture

# --- Инициализация приложения ---
app = Ursina()

# --- Параметры игры ---
with open("Settings.txt", "r") as file:
	GRID_SIZE = int(file.readline())  # Размер сетки
	MINES_COUNT = int(file.readline())  # Количество мин

# --- Игровые переменные ---
grid = []
game_over = False
mines_placed = False
mini_blocks = []
dialogue_num = 0
current_dialogue_num = None
dialogue_sound = Audio()
game_sounds = Audio()
nerd_model = Entity(visible=False, rotation=(-90, 180, 0), scale=0.7)
nerd_model_details = {
	"Brown": Entity(model="Models/Nerd/Brown.ply", color=color.brown, parent=nerd_model),#, scale=1.1, y=1),
	"White": Entity(model="Models/Nerd/White.ply", color=color.rgb(0.8, 0.7, 0.6), parent=nerd_model),
	"Blue": Entity(model="Models/Nerd/Blue.ply", color=color.rgb(0.3, 0.5, 0.8), parent=nerd_model),#, scale=1.2),
	"Black": Entity(model="Models/Nerd/Black.ply", color=color.rgb(0.1, 0.1, 0.1), parent=nerd_model),
	}
game_ended = False
game_sounds_playing = False

def popup(text="Сообщение", on_continue=None, text_scale=2, emoji_texture=None):

	"""
	Создаёт всплывающее окно с настраиваемым текстом и кнопкой "Продолжить".
	text: Текст сообщения в окне.
	on_continue: Функция, вызываемая при нажатии на "Продолжить".
	"""

	# Окно
	popup = Entity(
		parent=camera.ui,
		model="quad",
		color=color.rgba(0, 0, 0, 0.5),
		scale=(0.8, 0.6),
		position=(0, 0, -0.5)
	)
	if emoji_texture is not None:
		# Смайлик
		emoji = Entity(
			parent=popup,
			model="quad",
			position=(0, 0.3),
			scale=(0.25, 0.3),
			texture=emoji_texture
		)
	
	# Текст в окне
	popup_text = Text(
		parent=popup,
		text=text,
		scale=text_scale,
		color=color.white,
		origin=(0, 0),
		position=(0, 0),
		wordwrap=10
	)

	# Функция закрытия окна
	def close_popup():
		global game_sounds
		game_sounds = Audio("Sounds/Button.mp3")
		destroy(popup)
		if on_continue:
			on_continue()
	# Кнопка "Продолжить"
	continue_button = Button(
		parent=popup,
		color=color.rgba(0, 0, 0, 0.5),
		scale=(0.5, 0.3),
		position=(0, -0.3),
		on_click=lambda: close_popup(),
		collider="box"
	)

	continue_text= Text("Продолжить", scale=text_scale, position=(0, -0.3), origin=(0, 0), parent=popup)

def show_dialogue(dialogue_texts, on_complete=None):

	"""
	Создает диалоговое окно с текстом, отображаемым по буквам.
	
	dialogue_texts: список строк для отображения в диалоге.
	on_complete: функция, вызываемая после завершения диалога.

	"""

	global is_showing_dialogue

	is_showing_dialogue = True

	dialogue_box = Entity(
		parent=camera.ui,
		model='quad',
		scale=(1.8, 0.3),
		color=color.black66,
		position=(0, -0.4),
		z=-1
	)
	
	dialogue_text = Text(
		text="",
		parent=dialogue_box,
		scale=(1, 5),
		position=(-50, 1),
		origin=(0, 0),
		line_height=1.1,  # Высота строки
		x=0,              # Смещение текста
		y=0.2             # Смещение текста
	)
	
	text_index = 0
	is_typing = False

	# Функция для переноса текста по ширине (например, 50 символов)
	def wrap_text(text):

		words = text.split(" ")
		lines = []
		current_line = ""
		
		for word in words:
			if len(current_line + " " + word) <= 75:
				current_line += " " + word if current_line else word
			else:
				lines.append(current_line)
				current_line = word

		if current_line:
			lines.append(current_line)

		return '\n'.join(lines)

	def type_text(text):

		nonlocal is_typing
		global dialogue_num, dialogue_sound

		dialogue_text.text = ""
		is_typing = True
		text = wrap_text(text)
		dialogue_num += 1
		dialogue_sound.stop()
		dialogue_sound = Audio(f"Dialogues/{dialogue_num}.mp3")

		def add_letter(i=0):

			nonlocal is_typing

			if is_typing:
				if i < len(text):
					dialogue_text.text += text[i]
					invoke(add_letter, i + 1, delay=0.02)  # Скорость появления букв
				else:
					is_typing = False
		
		add_letter()
	
	def next_dialogue():

		global is_showing_dialogue
		nonlocal text_index, is_typing
		if is_typing:
			# Если текст ещё печатается — мгновенно отобразить весь текст
			dialogue_text.text = wrap_text(dialogue_texts[text_index])
			is_typing = False
		else:
			text_index += 1
			if text_index < len(dialogue_texts):
				type_text(dialogue_texts[text_index])
			else:
				# Завершение диалога
				dialogue_box.disable()
				dialogue_text.disable()
				is_showing_dialogue = False
				if on_complete:
					on_complete()
	
	# Начинаем с первого текста
	type_text(dialogue_texts[text_index])
	
	# Обработка нажатия клавиш
	def input(key):
		if key.endswith(" up"):
			next_dialogue()
	
	dialogue_box.input = input

# --- Генерация сетки ---
def create_grid():

	global grid
	grid = []
	for x, y, z in product(range(GRID_SIZE), range(GRID_SIZE), range(GRID_SIZE)):
		# Внутренний куб (основной блок)
		uzbek = random.randint(1, 100000)
		block = Entity(model="cube", texture=("Textures/Uzbeki spyat.mp4" if uzbek == 1 else "Textures/Cell.png"), position=(x - GRID_SIZE * 0.5, y - GRID_SIZE * 0.5, z - GRID_SIZE * 0.5), collider="box")

		grid.append({
			"entity": block,
			"is mine": False,
			"is_revealed": False,
			"is flagged": False,
			"mines_around": 0,
			"uzbek": uzbek == 1,
			"hovered": False,
			"dop flag": None
		})


# --- Расстановка мин ---
def place_mines():
	mine_positions = random.sample(grid, MINES_COUNT)
	for mine in mine_positions:
		mine["is mine"] = True


# --- Поиск соседей ---
def get_neighbors(block, find_mini_blocks=False, from_mini_block=False):
	x, y, z = (block if from_mini_block else block["entity"]).position
	neighbors = []

	for dx in [-1, 0, 1]:
		for dy in [-1, 0, 1]:
			for dz in [-1, 0, 1]:
				if dx == dy == dz == 0:
					continue
				if find_mini_blocks:
					neighbor = next((b for b in mini_blocks if b.position == (x + dx, y + dy, z + dz)), None)
				else:
					neighbor = next((b for b in grid if b["entity"].position == (x + dx, y + dy, z + dz)), None)
				if neighbor:
					neighbors.append(neighbor)
	return neighbors


def calculate_mines():
	grid_dict = {(block["entity"].position.x, block["entity"].position.y, block["entity"].position.z): block for block in grid}
	
	for block in grid:
		if block["is mine"]:
			continue
		
		x, y, z = block["entity"].position
		mines_around = 0
		
		# Перебираем только 26 соседей
		for dx in [-1, 0, 1]:
			for dy in [-1, 0, 1]:
				for dz in [-1, 0, 1]:
					if dx == 0 and dy == 0 and dz == 0:
						continue
		
					neighbor_pos = (x + dx, y + dy, z + dz)
					neighbor = grid_dict.get(neighbor_pos)
					
					if neighbor and neighbor["is mine"]:
						mines_around += 1
		
		block["mines_around"] = mines_around

def shrink_and_destroy(block_entity, duration=0.3):
	"""
	Постепенно уменьшает блок и уничтожает его по завершению.
	block_entity: Entity, который будет уменьшен.
	duration: Время в секундах до полного уничтожения.
	"""
	if not block_entity:
		return
	
	original_scale = block_entity.scale
	steps = 5  # Количество шагов уменьшения
	interval = duration / steps  # Интервал между шагами
	
	def shrink_step(step=0):
		if step >= steps:
			destroy(block_entity)  # Уничтожаем блок
			return
		
		scale_factor = 1 - (step / steps)  # Уменьшаем масштаб
		block_entity.scale = original_scale * scale_factor
		invoke(shrink_step, step + 1, delay=interval)
	shrink_step()

def change_color(block, mini_block):
	
	block["hovered"] = True
	block["entity"].animate_color(color.rgb(0.9, 0.9, 1.0), duration=0.3, curve=curve.in_out_quad)
	def check_block():
		if mini_block != mouse.hovered_entity:
			block["entity"].animate_color(color.rgb(1.0, 1.0, 1.0), duration=0.3, curve=curve.in_out_quad)
			block["hovered"] = False
			return
		invoke(check_block, delay=0.1)
	check_block()

# --- Открытие блока ---
def reveal_block(block):

	global mines_placed, game_sounds, game_sounds_playing

	if block["is_revealed"] or block["is flagged"]:
		return

	block["is_revealed"] = True

	if not mines_placed:
		while True:
			place_mines()
			calculate_mines()
			if not block["is mine"] and block["mines_around"] == 0:
				break
			else:
				for b in grid:
					b["is mine"] = False
					b["mines_around"] = 0
		mines_placed = True

	if block["is mine"]:
		shrink_and_destroy(block["entity"])
		grid.append({"entity": Entity(model="Models/Mine.obj", position=block["entity"].position, texture="Textures/Cell.png", color=color.black, scale=0.5), "is mine": False, "is_revealed": False, "is flagged": False, "mines_around": 0, "uzbek": False, "hovered": False})
		for b in mini_blocks:
			shrink_and_destroy(b)
		for b in grid:
			b["entity"].color = (255, 255, 255, 0.3)
			if b["is mine"]:
				b["entity"].model = "Models/Mine.obj"
				b["entity"].color = color.black
				b["entity"].scale = 0.5
		global game_over
		game_over = True
		return

	block["entity"].color = color.white
	if block["mines_around"] > 0:
		mini_blocks.append(Entity(model="Models/Number cube.obj",texture=f"Textures/{block["mines_around"]}.png", color=color.light_gray, position=block["entity"].position, collider="box", scale=0.3))
	else:
		for neighbor in get_neighbors(block):
			if not neighbor["is_revealed"]:
				reveal_block(neighbor)
	shrink_and_destroy(block["entity"])
	grid.remove(block)
	if not game_sounds_playing:
		game_sounds = Audio("Sounds/Pup.mp3")
		game_sounds_playing = True


# --- Управление вводом ---
def input(key):
	global Menu, Settings, Education, game_ended, game_sounds, game_sounds_playing
	
	if Menu and key == "left mouse down":
	
		if play_button == mouse.hovered_entity:
			
			game_sounds = Audio("Sounds/Button.mp3")
			Menu = False
			play_button.visible = False
			settings_button.visible = False
			education_button.visible = False
			education_text.visible = False
			play_text.visible = False
			settings_text.visible = False
			menu_bg.visible = False
			settings_button.collider = None
			play_button.collider = None
			education_button.collider = None
			game_ended = False
			create_grid()
			EditorCamera()
			
		if settings_button == mouse.hovered_entity:
			
			game_sounds = Audio("Sounds/Button.mp3")
			Menu = False
			Settings = True
			play_button.visible = False
			settings_button.visible = False
			education_button.visible = False
			education_text.visible = False
			play_text.visible = False
			settings_text.visible = False
			settings_button.collider = None
			play_button.collider = None
			education_button.collider = None
			settings_bg.visible = True
			grid_size_slider.visible = True
			mines_count_slider.visible = True
			grid_size_slider.enabled = True
			mines_count_slider.enabled = True
			settings_continue_button.visible = True
			settings_continue_text.visible = True
			settings_continue_button.collider = "box"
			return
			
		if education_button == mouse.hovered_entity:
			
			game_sounds = Audio("Sounds/Button.mp3")
			Menu = False
			Education = True
			play_button.visible = False
			settings_button.visible = False
			education_button.visible = False
			education_text.visible = False
			play_text.visible = False
			settings_text.visible = False
			menu_bg.visible = False
			settings_button.collider = None
			play_button.collider = None
			education_button.collider = None
			
			def end_education():
			
				global Menu, game_ended, Education, grid, dialogue_num
				
				Menu = True
				Education = False
				play_button.visible = True
				settings_button.visible = True
				education_button.visible = True
				education_text.visible = True
				play_text.visible = True
				settings_text.visible = True
				menu_bg.visible = True
				settings_button.collider = "box"
				play_button.collider = "box"
				education_button.collider = "box"
				game_ended = True
				for b in grid: destroy(b)
				grid = []
				game_over = False
				mines_placed = False
				EditorCamera()
				EditorCamera.enabled = False
				nerd_model.visible = False
				dialogue_num = 0
				camera.position = (0, 0, -20)
				
				
			show_dialogue(["*Нажмите любую клавишу, чтобы начать обучение*", "Привет, я Нёрдик!", "Сейчас я расскажу тебе о том, как играть в Сапёр-3D. Это легче, чем кажется.", "Стоит начать с объяснений правил обычного сапёра.", "На игровом поле случайным образом разбросаны мины. Цель игрока - обозначить все мины на карте и открыть все пустые клетки.", "Белые клетки уже открыты, а серые - ещё нет.", "На некоторых клетках видны цифры, которые показывают количество мин вокруг него.", "Вокруг этой клетки находится 2 мины", "Вокруг этой клетки всего 1 мина", "А вокруг тех, что без цифр, мин нету.", "Теперь снова обратим внимание на эту клетку. Рядом с ней не открыто 2 клетки, а так же, вокруг неё 2 мины. Совпадение?", "Нет, это не совпадение. Эти 2 клетки точно являются минами, ведь больше неоткрытых клеток нету.", "Есть и обратная тактика - искать НЕ мины. Раз вокруг этой клетки 2 мины, а мы их уже нашли, то остальные клетки можно открыть.", "Конечно, есть и другие, более сложные способы нахождения мин, но я объяснил только самые основные, которые применяются чаще всего.", "Теперь посмотрим, как это будет выглядеть в 3D", "Как мы видим, вокруг каждой клетки уже не 8 соседей, а целых 26! Каждый из них относится к указанной клетке и может быть миной. Решать тут надо по таким же тактикам.", "Так же, в игре есть маленькие блоки с цифрами, которые указывают на количество мин вокруг них. Если навести курсор на одного из них, то соседние клетки выделятся.", "Отлично, теперь про управление. Правая кнопка мыши позволит поставить флажок, а если её зажать, то можно вращать камеру.", "Чтобы открыть блок, нажми левой кнопкой мыши, а чтобы изменить положение точки вращения камеры, удерживай среднюю кнопку мыши.", "Поздравляю, обучение пройдено! Если что-то не понятно, пересмотри ещё раз. Удачи!"], end_education)
			
	if Settings and key == "left mouse down" and settings_continue_button == mouse.hovered_entity:
	
		Menu = True
		play_button.visible = True
		settings_button.visible = True
		education_button.visible = True
		education_text.visible = True
		play_text.visible = True
		settings_text.visible = True
		menu_bg.visible = True
		settings_button.collider = "box"
		play_button.collider = "box"
		education_button.collider = "box"
		settings_bg.visible = False
		grid_size_slider.visible = False
		mines_count_slider.visible = False
		grid_size_slider.enabled = False
		mines_count_slider.enabled = False
		settings_continue_button.visible = False
		settings_continue_text.visible = False
		settings_continue_button.collider = None
		game_sounds = Audio("Sounds/Button.mp3")
		
		with open("Settings.txt", "w", encoding="utf-8") as f:
			f.write(f"{GRID_SIZE}\n{MINES_COUNT}")
	
	if game_over: return

	hit_info = mouse.hovered_entity
	if not hit_info:
		return

	block = next((b for b in grid if b["entity"] == hit_info), None)
	
	if block:
		if key in ["right mouse down", "left mouse down"] and block["uzbek"]:
			popup("Поздравляю, вы нашли посхалко! С шансом 0.001% появляется такая текстура")
			block["uzbek"] = False

		if key == "left mouse down":
			game_sounds_playing = False
			reveal_block(block)

		if key == "right mouse down" and not block["is_revealed"]:
			if block["is flagged"]:
				block["entity"].model = "cube"
				block["entity"].color = color.white
				block["entity"].texture = "Textures/Cell.png"
				block["entity"].collider = "box"
				block["is flagged"] = False
				destroy(block["dop flag"])
				game_sounds = Audio("Sounds/Pop.mp3")
			else:
				block["entity"].model = "Models/Flag.obj"
				block["entity"].color = color.rgb(0.3, 0.3, 0.3)
				block["entity"].collider = "mesh"
				block["dop flag"] = Entity(model="Models/Red flag.obj", parent=block["entity"], color=color.red)
				block["is flagged"] = True
				game_sounds = Audio("Sounds/Pop.mp3")

		for b in get_neighbors(block, True):
			if all([n["is flagged"] for n in get_neighbors({"entity": b})]):
				shrink_and_destroy(b)
				mini_blocks.remove(b)

menu_bg = Entity(model="quad", texture="Textures/Menu bg.mp4", z=1, scale=(window.aspect_ratio * 10, 10))
play_button = Entity(
	parent=camera.ui,
	model="quad",
	color=(0, 0, 0, 0.5),
	scale=(0.5, 0.25),
	z=-1,
	y=0.3,
	collider="box"
)
play_button_hovered = False
play_text = Text("Начать игру", origin=(0, 0), scale=2, y=0.3)

settings_button = Entity(
	parent=camera.ui,
	model="quad",
	color=(0, 0, 0, 0.5),
	scale=(0.5, 0.25),
	z=-1,
	collider="box"
)
settings_button_hovered = False
settings_text = Text("Настройки", origin=(0, 0), scale=2)

education_button = Entity(
	parent=camera.ui,
	model="quad",
	color=(0, 0, 0, 0.5),
	scale=(0.5, 0.25),
	z=-1,
	y=-0.3,
	collider="box"
)
education_button_hovered = False
education_text = Text("Обучение", origin=(0, 0), scale=2, y=-0.3)
Education = False

def update_sliders():
	global GRID_SIZE, MINES_COUNT
	GRID_SIZE = grid_size_slider.value
	MINES_COUNT = min(mines_count_slider.value, GRID_SIZE ** 3)

settings_bg = Entity(parent=camera.ui, model="quad", color=color.rgba(0, 0, 0, 0.5), scale=(1.5, 0.8), visible=False)
grid_size_slider = Slider(1, 200, default=GRID_SIZE, step=1, text="Размер сетки", position=(-0.24, 0.2), scale=(1.5, 1.5), origin=(0, 0), visible=False, on_value_changed=update_sliders, enabled=False)
mines_count_slider = Slider(1, GRID_SIZE ** 3, default=MINES_COUNT, step=1, text="Количество мин", position=(-0.24, 0), scale=(1.5, 1.5), origin=(0, 0), visible=False, on_value_changed=update_sliders, enabled=False)
settings_continue_button = Entity(parent=camera.ui, model="quad", color=color.rgba(0, 0, 0, 0.5), scale=(0.5, 0.25), position=(0, -0.2), visible=False)
settings_continue_button_hovered = False
settings_continue_text = Text("Подтвердить", origin=(0, 0), scale=2, y=-0.2, visible=False)
Settings = False

def end_game():

	global Menu, game_ended, grid, game_over, mines_placed, mini_blocks

	Menu = True
	play_button.visible = True
	settings_button.visible = True
	education_button.visible = True
	education_text.visible = True
	play_text.visible = True
	settings_text.visible = True
	menu_bg.visible = True
	settings_button.collider = "box"
	play_button.collider = "box"
	education_button.collider = "box"
	game_ended = True
	for b in grid: destroy(b["entity"])
	grid = []
	game_over = False
	mines_placed = False
	for mini_blocks in grid: destroy(b)
	mini_blocks = []
	EditorCamera()
	EditorCamera.enabled = False

def update():

	global play_button_hovered, settings_button_hovered, education_button_hovered, settings_continue_button_hovered, Menu, Education, game_ended, current_dialogue_num, grid, game_sounds
	
	mini_block = next((b for b in mini_blocks if b == mouse.hovered_entity), None)
	if mini_block:
		for b in get_neighbors(mini_block, from_mini_block=True):
			if not b["hovered"] and not b["is flagged"]:
				change_color(b, mini_block)
	# Меню
	if Menu:
	
		if play_button == mouse.hovered_entity:
			if not play_button_hovered:
				play_button.animate_color(color.rgba(0, 0, 0, 0.7), duration=0.2, curve=curve.in_out_quad)
				play_button_hovered = True
		elif play_button_hovered:
			play_button.animate_color((0, 0, 0, 0.5), duration=0.2, curve=curve.in_out_quad)
			play_button_hovered = False
			
		if settings_button == mouse.hovered_entity:
			if not settings_button_hovered:
				settings_button.animate_color(color.rgba(0, 0, 0, 0.7), duration=0.2, curve=curve.in_out_quad)
				settings_button_hovered = True
		elif settings_button_hovered:
			settings_button.animate_color((0, 0, 0, 0.5), duration=0.2, curve=curve.in_out_quad)
			settings_button_hovered = False
			
		if education_button == mouse.hovered_entity:
			if not education_button_hovered:
				education_button.animate_color(color.rgba(0, 0, 0, 0.7), duration=0.2, curve=curve.in_out_quad)
				education_button_hovered = True
		elif education_button_hovered:
			education_button.animate_color((0, 0, 0, 0.5), duration=0.2, curve=curve.in_out_quad)
			education_button_hovered = False
			
	# Настройки
	
	elif Settings:
		
		GRID_SIZE = grid_size_slider.value
		MINES_COUNT = mines_count_slider.value
		mines_count_slider.max = GRID_SIZE ** 3
		if mines_count_slider.value > mines_count_slider.max:
			MINES_COUNT = mines_count_slider.max
			mines_count_slider.value = mines_count_slider.max
		
		if settings_continue_button == mouse.hovered_entity:
			if not settings_continue_button_hovered:
				settings_continue_button.animate_color(color.rgba(0, 0, 0, 0.7), duration=0.2, curve=curve.in_out_quad)
				settings_continue_button_hovered = True
		elif settings_continue_button_hovered:
			settings_continue_button.animate_color((0, 0, 0, 0.5), duration=0.2, curve=curve.in_out_quad)
			settings_continue_button_hovered = False
			
	elif not game_ended and not Education:
		
		if game_over:
			popup("Вы програли, сочувствую...", emoji_texture="Textures/Sad emoji.png", on_continue=end_game)
			game_ended = True
		if check_win():
			popup("Поздравляю, вы выиграли!", emoji_texture="Firecracker.png", on_continue=end_game)			
			game_ended = True
			
	if current_dialogue_num != dialogue_num:
	
		current_dialogue_num = dialogue_num
		match dialogue_num:
			case 1:
				EditorCamera()
				nerd_model.position = (0, -10, 0)
				nerd_model.visible = True
				nerd_model.animate_position((0, 0, 0), curve=curve.in_out_quad, duration=0.5)
			case 2:
				nerd_model.animate_rotation((-90, 200, 0), curve=curve.in_out_quad, duration=0.5)
			case 3:
				nerd_model.animate_rotation((-90, 160, 0), curve=curve.in_out_quad, duration=0.5)
			case 4:
				nerd_model.animate_rotation((-90, 200, 0), curve=curve.in_out_quad, duration=0.5)
				nerd_model.animate_position((5, 0.5, 0), curve=curve.in_out_quad, duration=0.5)
				
				grid = [
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.8, 0.4), parent=camera.ui),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.65, 0.4), parent=camera.ui),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.5, 0.4), parent=camera.ui),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.35, 0.4), parent=camera.ui),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.2, 0.4), parent=camera.ui),
					Entity(model="Models/Number cube.obj", texture="Textures/1.png", scale=0.25, position=(-0.05, 0.4), parent=camera.ui),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(0.1, 0.4), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(0.25, 0.4), parent=camera.ui, color=color.gray),
					
					Entity(model="Models/Number cube.obj", texture="Textures/1.png", scale=0.25, position=(-0.8, 0.25), parent=camera.ui),
					Entity(model="Models/Number cube.obj", texture="Textures/1.png", scale=0.25, position=(-0.65, 0.25), parent=camera.ui),
					Entity(model="Models/Number cube.obj", texture="Textures/1.png", scale=0.25, position=(-0.5, 0.25), parent=camera.ui),
					Entity(model="Models/Number cube.obj", texture="Textures/2.png", scale=0.25, position=(-0.35, 0.25), parent=camera.ui),
					Entity(model="Models/Number cube.obj", texture="Textures/2.png", scale=0.25, position=(-0.2, 0.25), parent=camera.ui),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.05, 0.25), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(0.1, 0.25), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(0.25, 0.25), parent=camera.ui, color=color.gray),
					
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.8, 0.1), parent=camera.ui, color=color.gray),
					Entity(model="Models/Number cube.obj", texture="Textures/1.png", scale=0.25, position=(-0.65, 0.1), parent=camera.ui),
					Entity(model="Models/Number cube.obj", texture="Textures/1.png", scale=0.25, position=(-0.5, 0.1), parent=camera.ui),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.35, 0.1), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.2, 0.1), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.05, 0.1), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(0.1, 0.1), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(0.25, 0.1), parent=camera.ui, color=color.gray),
					
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.8, -0.05), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.65, -0.05), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.5, -0.05), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.35, -0.05), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.2, -0.05), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(-0.05, -0.05), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(0.1, -0.05), parent=camera.ui, color=color.gray),
					Entity(model="cube", texture="Textures/Cell.png", scale=0.15, position=(0.25, -0.05), parent=camera.ui, color=color.gray),
				]
				for b in grid:
					if b.scale == 0.15:
						b.scale = 0.001
						b.animate_scale((0.15, 0.15), curve=curve.in_out_quad, duration=0.5)
					else:
						b.scale = 0.001
						b.animate_scale((0.25, 0.25), curve=curve.in_out_quad, duration=0.5)
			
			case 8:
				grid[2].animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[3].animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[4].animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[10].animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[11].animate_color(color.rgb(0.8, 0.8, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[12].animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[18].animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[19].animate_color(color.rgb(0.6, 0.6, 0.7), curve=curve.in_out_quad, duration=0.5)
				grid[20].animate_color(color.rgb(0.6, 0.6, 0.7), curve=curve.in_out_quad, duration=0.5)
				
			case 9:
				grid[3].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[4].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[11].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[12].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[19].animate_color(color.gray, curve=curve.in_out_quad, duration=0.5)
				grid[20].animate_color(color.gray, curve=curve.in_out_quad, duration=0.5)
				
				grid[0].animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[1].animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[8].animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[9].animate_color(color.rgb(0.8, 0.8, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[16].animate_color(color.rgb(0.6, 0.6, 0.7), curve=curve.in_out_quad, duration=0.5)
				grid[17].animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
				
			case 10:
			
				grid[8].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[9].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[10].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[16].animate_color(color.gray, curve=curve.in_out_quad, duration=0.5)
				grid[17].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[18].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				
				grid[3].animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[4].animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
				
			case 11:
			
				grid[0].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[1].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[2].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[3].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[4].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				
				grid[11].animate_color(color.rgb(0.8, 0.8, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[19].texture = "Textures/Flag.png"
				grid[20].texture = "Textures/Flag.png"
				
			case 12:
			
				grid[11].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				grid[12].animate_color(color.rgb(0.8, 0.8, 1.0), curve=curve.in_out_quad, duration=0.5)
				
			case 13:
				grid[13].color = color.rgb(1.0, 1.0, 1.0)
				grid[21].color = color.rgb(1.0, 1.0, 1.0)
				grid[13].texture = "Textures/1.png"
				grid[21].texture = "Textures/1.png"
				grid[13].model = "Models/Number cube.obj"
				grid[21].model = "Models/Number cube.obj"
				grid[13].size = 0.001
				grid[21].size = 0.001
				grid[13].animate_scale((0.25, 0.25), curve=curve.in_out_quad, duration=0.5)
				grid[21].animate_scale((0.25, 0.25), curve=curve.in_out_quad, duration=0.5)
				
			case 14:
			
				grid[11].animate_color(color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5)
				
				
			case 15:
				for b in grid: 
					b.animate_scale((0.001, 0.001), curve=curve.in_out_quad, duration=0.5)
				def delete_blocks():
					for b in grid: destroy(b)
				invoke(delete_blocks, delay=0.5)
				invoke(nerd_model.animate_rotation, (-90, 0, 0), curve=curve.in_out_quad, duration=0.5, delay=0.5)
				invoke(nerd_model.animate_position, (-5, 1, 0), curve=curve.in_out_quad, duration=0.5, delay=0.5)
				EditorCamera()
				grid = []
				def add_new_blocks():
					for x in range(3):
						for y in range(3):
							for z in range(3):
								grid.append(Entity(model="cube", position=(x, y, z), texture="Textures/Cell.png", scale=0.001))
								grid[-1].animate_scale((1, 1, 1), curve=curve.in_out_quad, duration=0.5)
				invoke(add_new_blocks, delay=1)
				invoke(camera.animate_position, Vec3(10, 5, -15), curve=curve.in_out_quad, duration=0.5, delay=0.5)
				invoke(camera.animate_rotation, Vec3(10, -30, 0), curve=curve.in_out_quad, duration=0.5, delay=0.5)
			
			case 16:
				
				for b in grid:
					b.animate_color(color.rgb(0.9, 0.9, 1.0), curve=curve.in_out_quad, duration=0.5)
					invoke(b.animate_color, color.rgb(1.0, 1.0, 1.0), curve=curve.in_out_quad, duration=0.5, delay=0.5)
				invoke(nerd_model.animate_rotation, (-90, 140, 0), curve=curve.in_out_quad, duration=0.5, delay=0.5)
					
			case 17:
				grid.append(Entity(model="Models/Number cube.obj",texture="Textures/1.png", color=color.light_gray, position=(3, 1, 0), collider="box", scale=0.001))
				grid[-1].animate_scale((0.3, 0.3, 0.3), curve=curve.in_out_quad, duration=0.5)
				grid.append(Entity(model="Models/Number cube.obj",texture="Textures/2.png", color=color.light_gray, position=(3, 2, 0), collider="box", scale=0.001))
				grid[-1].animate_scale((0.3, 0.3, 0.3), curve=curve.in_out_quad, duration=0.5)
				grid.append(Entity(model="Models/Number cube.obj",texture="Textures/2.png", color=color.light_gray, position=(3, 2, 1), collider="box", scale=0.001))
				grid[-1].animate_scale((0.3, 0.3, 0.3), curve=curve.in_out_quad, duration=0.5)
				grid.append(Entity(model="Models/Number cube.obj",texture="Textures/1.png", color=color.light_gray, position=(3, 2, -3), collider="box", scale=0.001))
				grid[-1].animate_scale((0.3, 0.3, 0.3), curve=curve.in_out_quad, duration=0.5)
			
# --- Проверка на победу ---
def check_win():
	
	for block in grid:
		if not block["is mine"] and not block["is_revealed"]:
			return False
	return True

Menu = True
Sky(texture="Textures/Skybox.png")
app.run()
