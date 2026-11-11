\# AVISADOR DE TAREAS v0.9.9.3



CORRECCIONES

\- Los avisos solo aparecen en el equipo cuyo técnico actual coincide con el técnico asignado a la tarea.

\- El filtro visual Todos/Técnico no modifica qué avisos recibe el equipo.

\- Sin asignar no genera avisos automáticos en todos los equipos.

\- Si el texto de una tarea está vacío aparece: Rellena el campo de la tarea.

\- El modo oscuro se ha retirado temporalmente.

\- Se utiliza únicamente el banner Light definitivo.

\- Calendario, Editar, Reprogramar, Reasignar, Opciones y Recordatorios usan el icono del Avisador.

\- Se mantiene la recarga del JSON cada minuto, técnicos compartidos, histórico y filtro visual.



CREAR EXE

Ejecuta Crear\_EXE\_Avisador\_v0.9.9.3.bat

Resultado: dist\\Avisador de Tareas v0.9.9.3.exe



\# AVISADOR DE TAREAS v0.9.2



CORRECCIONES VISUALES

* Botones redondeados renderizados con antialias a 4x mediante Pillow.
* El hover y el clic no mueven ni un pixel la geometria del boton o su sombra: solo cambia el color.
* Eliminado ttk.Notebook para Pendientes/Historico.
* Pendientes e Historico son ahora pestañas propias de ancho y alto exactamente iguales.
* La seleccion solo modifica color de fondo/texto, nunca dimensiones, relieve ni padding.
* Se conservan las funciones de v0.9.1: menus con boton derecho, historico manual/automatico, prioridades, reprogramar, avisos e icono optimizado.



\# AVISADOR DE TAREAS v0.9.1

* Corregido el salto visual de 1-2 px de los botones al pasar/pulsar con el raton.
* Pestanas Pendientes/Historico mantienen el mismo tamano seleccionado o no.
* Las tareas ya marcadas como realizadas en versiones antiguas pasan al Historico al migrar.
* Boton derecho sobre una tarea pendiente: Editar, Reprogramar, Realizada/Pendiente, Prioritaria/Normal, Enviar a Historico y Eliminar.
* Boton derecho en Historico: Restaurar/Reprogramar o Eliminar.
* Enviar a Historico fuerza el archivado inmediato sin esperar 24 horas.
* Las tareas nuevas marcadas Realizada siguen esperando 24 horas antes de pasar automaticamente a Historico.
* Icono optimizado incluido en el EXE.



\# AVISADOR DE TAREAS v0.8



Correcciones:

* Editar: ventana centrada de 560 x 470, completa y visible.
* Reprogramar: ventana centrada de 480 x 280, completa y visible.
* Se corrige el formato de geometria incompleto de la v0.7.1.
* Las ventanas ya no se pueden maximizar para evitar el panel blanco.
* Mantiene la barra de acciones y todas las funciones anteriores.



\#AVISADOR DE TAREAS v0.7



Cambios:

* Interfaz renovada y tipografia Segoe UI.
* Avisos previos: caducan en 60 segundos y reaparecen hasta 3 veces.
* Aviso de la hora exacta: no caduca y sustituye cualquier aviso previo de esa tarea.
* Tareas vencidas sin atender: rojo y negrita.
* Tareas realizadas: verde.
* Boton Reprogramar: cambia solamente fecha y hora.
* Iconos integrados correctamente en el EXE.

