from webob import Request,Response
from parse import parse
import inspect
import colorama
from wsgiadapter import WSGIAdapter as RequestsWSGIAdapter
import os
from jinja2 import Environment, FileSystemLoader
from whitenoise import WhiteNoise
from middleware import Middleware
colorama.init()

class API:
    def __init__(self,templates_dir="templates", static_dir="static"):
        self.routes={}
        self.exception_handler =None
        self.templates_env = Environment(loader =FileSystemLoader(os.path.abspath(templates_dir)))
        self.whitenoise = WhiteNoise(self.wsgi_app, root=static_dir)
        self.middleware = Middleware(self)
        
        
    def add_middleware(self,middleware_cls):
        self.middleware.add(middleware_cls)
        
    def add_exception_handler(self,exception_handler):
        self.exception_handler = exception_handler
        
    def template(self,template_name,context=None):
        if context is None:
            context={}
        return self.templates_env.get_template(template_name).render(**context)        
    
    def route(self,path):
        if path in self.routes :
            raise AssertionError('Such route already exists')
        def wrapper(handler):
            self.routes[path] =handler
            print(colorama.Fore.GREEN,"handler check",handler)
            return handler
        return wrapper
    
    def add_route(self,path,handler):
        if path in self.routes:
            raise AssertionError('Such route already exists')
        self.routes[path] =handler
        
        
        
    def __call__(self, environ, start_response):
        print("CALLED __CALL__")
        path_info = environ["PATH_INFO"]
        if path_info.startswith("/static"):
            environ["PATH_INFO"] = path_info[len("/static"):]
            return self.whitenoise(environ, start_response)
        return self.middleware(environ, start_response)
    
    def wsgi_app(self, environ, start_response):
        request =Request(environ)
        
        response =self.handle_request(request)
        
        return response(environ,start_response)
        
    
    def default_response(self,response):
        response.status_code = 404
        response.text = "Not found."
        
    
    def find_handler(self,request_path):
        for path,handler in self.routes.items():
            print("path is ",path)
            print("request_path is ",request_path)
            parse_result = parse(path,request_path)
            if parse_result is not None:
                print("handler named ",handler, parse_result.named)
                return handler,parse_result.named
            
        return None,None    
            
    
    def handle_request(self,request):
        response =Response()
        print(colorama.Fore.RED,"request is  ",request)
        
        handler,kwargs = self.find_handler(request_path=request.path)
        try:
            if handler is not None:
                if inspect.isclass(handler):
                    handler = getattr(handler(),request.method.lower(),None)
                    if handler is None:
                        raise AttributeError('Method is not allowed ',request.method.lower())             
                handler(request,response,**kwargs)
            else:
                self.default_response(response) 
        except Exception as e:
            if self.exception_handler is None:
                print("raised")
                raise e
            else:
                self.exception_handler(request, response, e)      
        return response   
    
    #test part
    def test_session(self, base_url="http://testserver"):
        session = RequestsSession()
        session.mount(prefix=base_url, adapter=RequestsWSGIAdapter(self))
        return session  
    
    
            
        
        
    