# Avisador de Tareas

Una aplicación sencilla para llevar el control de tus tareas y no olvidarte nada. Drap Style. Diseñada para utilizar por varios técnicos

# Como ejecutarlo

1. Ejecuta Crear\_EXE\_Avisador\_v0.9.9.3.bat
2. Ejecutar el exe. Lo encontrarás en dist\Avisador de Tareas v0.9.9.3.exe



# Donde se almacenan las tareas

Las tareas siguen en %USERPROFILE%\\avisador\_tareas.json y son compatibles con las versiones anteriores.


# Lista de cambios

## v0.9.9.3

\- Los avisos solo aparecen en el equipo cuyo técnico actual coincide con el técnico asignado a la tarea.

\- El filtro visual Todos/Técnico no modifica qué avisos recibe el equipo.

\- Sin asignar no genera avisos automáticos en todos los equipos.

\- Si el texto de una tarea está vacío aparece: Rellena el campo de la tarea.

\- El modo oscuro se ha retirado temporalmente.

\- Se utiliza únicamente el banner Light definitivo.

\- Calendario, Editar, Reprogramar, Reasignar, Opciones y Recordatorios usan el icono del Avisador.

\- Se mantiene la recarga del JSON cada minuto, técnicos compartidos, histórico y filtro visual.

## v0.9.9.2

\- Añadido filtro visible «Filtrar por técnico».

\- «Todos» muestra todas las tareas.

\- Elegir un técnico muestra únicamente sus tareas en Pendientes e Histórico.

\- El filtro es únicamente visual: no altera tareas, asignaciones ni avisos.

\- El desplegable se actualiza automáticamente cuando cambia la lista compartida de técnicos.

\- Se incluyen sin modificar los nuevos banners editados por Carlos.

\- Mantiene calendario, modo oscuro, recarga de red cada minuto y técnicos compartidos.


## v0.9.9

\- Banner horizontal centrado creado a partir del diseño generado de Avisador de Tareas y el logo ADICO.

\- Banner claro y banner oscuro integrados en el EXE.

\- Botón Modo oscuro / Modo claro en la cabecera.

\- La preferencia de apariencia se guarda en config.json.

\- Fondo claro más oscuro y con mayor contraste.

\- Modo oscuro aplicado a fondo, tarjetas, textos, campos y listado.

\- Corregido el icono de bandeja: Abrir es la acción predeterminada. Un clic/doble clic sobre el icono abre y enfoca la ventana sin entrar en el menú.

\- Mantiene técnicos compartidos, eliminación de técnicos, recarga cada minuto y listado sin columna AVISOS.


## v0.9.8.1

Fallo corregido:
AttributeError: '\_tkinter.tkapp' object has no attribute 'shared\_technicians'

Causa:
La interfaz intentaba crear los desplegables de técnicos antes de inicializar shared\_technicians.

Corrección:
\- shared\_technicians se inicializa antes de ui().

\- El JSON compartido se carga antes de construir los desplegables.

\- Si el JSON no puede leerse, se utiliza de forma segura «Sin asignar».

\- Mantiene la eliminación de técnicos, el límite de 10 caracteres, la comparación sin mayúsculas/acentos, la recarga cada minuto y la lista sin columna AVISOS.

## v0.9.8

\- Técnicos almacenados dentro del JSON compartido.

\- Nombres únicos sin distinguir mayúsculas, minúsculas ni acentos.

\- Máximo 10 caracteres por técnico.

\- Opciones permite elegir, crear y eliminar técnicos.

\- Al eliminar un técnico con tareas: Sí elimina también sus tareas; No conserva las tareas como Sin asignar; Cancelar no cambia nada.

\- Columna AVISOS eliminada del listado. Los recordatorios siguen funcionando.

\- Recarga automática del JSON cada 60 segundos para compartir cambios entre equipos.

\- El JSON antiguo en formato lista se migra automáticamente al nuevo formato con technicians y tasks.

## v0.9.7

\- Opciones incluye selector de técnico actual y botón Cambiar técnico.

\- Opciones incluye botón Nuevo técnico.

\- Cada tarea conserva su técnico asignado en el JSON.

\- Nuevo botón Reasignar en la barra principal.

\- Opción Reasignar en el menú contextual de las tareas pendientes.

\- Reasignar permite elegir un técnico existente o crear uno nuevo.

\- Las tareas restauradas desde Histórico conservan el técnico.

\- Se mantiene la selección de JSON local o compartido desde Opciones.

\- Se mantiene el guardado atómico mediante archivo temporal.

## v0.9.6

\- Campo Tecnico al crear cada tarea.

\- Columna Tecnico en Pendientes e Historico.

\- Boton Reasignar en la barra principal.

\- Opcion Reasignar en el menu contextual de las tareas pendientes.

\- Ventana Reasignar para cambiar solamente el tecnico de la tarea.

\- Opciones incluye Cambiar tecnico para seleccionar el tecnico predeterminado del equipo.

\- Opciones permite elegir la ubicacion del JSON de tareas, incluida una ruta compartida.

\- Configuracion local guardada en %LOCALAPPDATA%\\AvisadorTareas\\config.json.

\- Las tareas antiguas sin tecnico se asignan al tecnico actual configurado.

\- Los avisos agrupados muestran el tecnico asociado a cada tarea.

\- Conserva Historico, prioridades, avisos agrupados y almacenamiento atomico del JSON.

\- Incluye el icono optimizado de 512 px y el ICO multiresolucion dentro del EXE.


## v0.9.5

\- Opciones con botón Cambiar técnico.

\- Técnico predeterminado local guardado en %LOCALAPPDATA%\\AvisadorTareas\\config.json.

\- Campo Técnico al crear y listar tareas.

\- Botón Reasignar y opción Reasignar en el menú contextual.

\- Las tareas antiguas reciben inicialmente el técnico actual.

\- Opción para seleccionar el JSON local o compartido mediante una ruta UNC.

\- Escritura atómica mediante archivo temporal para reducir el riesgo de corrupción.

\- Avisos agrupados cuando varias tareas coinciden en fecha y hora.


## v0.9.4

\- Opciones > almacenamiento LOCAL o COMPARTIDO.

\- LOCAL usa %USERPROFILE%\\avisador\_tareas.json.

\- COMPARTIDO permite seleccionar un JSON en una ruta UNC o unidad de red.

\- Recarga automática cada 3 segundos para detectar cambios realizados desde otros equipos.

\- Escritura atómica mediante archivo temporal y sustitución del JSON.

\- Archivo .lock para impedir dos escrituras simultáneas. Los bloqueos obsoletos se liberan tras 30 segundos.

\- Selector de técnico en la cabecera.

\- Recuerda localmente el último técnico seleccionado y lo preselecciona la próxima vez.

\- Opciones permite mantener la lista de técnicos.

\- Las tareas nuevas guardan el técnico que las creó.


## v0.9.2

\- Botones redondeados renderizados con antialias a 4x mediante Pillow.

\- El hover y el clic no mueven ni un pixel la geometria del boton o su sombra: solo cambia el color.

\- Eliminado ttk.Notebook para Pendientes/Historico.

\- Pendientes e Historico son ahora pestañas propias de ancho y alto exactamente iguales.

\- La seleccion solo modifica color de fondo/texto, nunca dimensiones, relieve ni padding.

\- Se conservan las funciones de v0.9.1: menus con boton derecho, historico manual/automatico, prioridades, reprogramar, avisos e icono optimizado.

## v0.9.1

\- Corregido el salto visual de 1-2 px de los botones al pasar/pulsar con el raton.

\- Pestanas Pendientes/Historico mantienen el mismo tamano seleccionado o no.

\- Las tareas ya marcadas como realizadas en versiones antiguas pasan al Historico al migrar.

\- Boton derecho sobre una tarea pendiente: Editar, Reprogramar, Realizada/Pendiente, Prioritaria/Normal, Enviar a Historico y Eliminar.

\- Boton derecho en Historico: Restaurar/Reprogramar o Eliminar.

\- Enviar a Historico fuerza el archivado inmediato sin esperar 24 horas.

\- Las tareas nuevas marcadas Realizada siguen esperando 24 horas antes de pasar automaticamente a Historico.

\- Icono optimizado incluido en el EXE.

## v0.8

\- Editar: ventana centrada de 560 x 470, completa y visible.

\- Reprogramar: ventana centrada de 480 x 280, completa y visible.

\- Se corrige el formato de geometria incompleto de la v0.7.1.

\- Las ventanas ya no se pueden maximizar para evitar el panel blanco.

\- Mantiene la barra de acciones y todas las funciones anteriores.

## v0.7

\- Interfaz renovada y tipografia Segoe UI.

\- Avisos previos: caducan en 60 segundos y reaparecen hasta 3 veces.

\- Aviso de la hora exacta: no caduca y sustituye cualquier aviso previo de esa tarea.

\- Tareas vencidas sin atender: rojo y negrita.

\- Tareas realizadas: verde.

\- Boton Reprogramar: cambia solamente fecha y hora.

\- Iconos integrados correctamente en el EXE.

