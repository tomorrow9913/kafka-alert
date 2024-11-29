import os

callback_files = [f[:-3] for f in os.listdir(os.path.dirname(__file__)) 
               if f.endswith('.py') and f != '__init__.py']

callbacks = []
for callback_file in callback_files:
   module = __import__(f'callback.{callback_file}', fromlist=['callback'])
   callbacks.append(module.callback)