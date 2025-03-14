### 大修改
### 2024.11.18 创建主函数，调用其他模块完成对话
### 2024.11.23 基于CodeCopilot进行代码重构，代码汇总至这一个文件
### 2024.11.26 代码框架分散化，提高可维护性
### 2025.03.14 添加GUI支持和参数交互能力
### 2025.03.15 添加多线程支持，避免界面卡顿

### ========== 导入辅助模块 ========== ###
from ChatInter import ChatGPT # 导入ChatGPT聊天接口
from TasksManager import TasksManager # 导入任务管理器

# 条件导入PySide6，当此脚本不是启动脚本时导入
if __name__ != '__main__':
    from PySide6.QtCore import QObject, Signal
    HAS_PYSIDE = True
else:
    ## 此脚本作为调试脚本debug时，不导入PySide6
    HAS_PYSIDE = False
    # 在调试的时候，创建一个简单的替代类
    class QObject: pass
    class Signal:
        def __init__(self, *args): pass
        def emit(self, *args): pass
    
### ========== 导入任务模块 ========== ###
from tasks.YOLOTasks import ObjDetect, HummanPoseTrack  # YOLO 图像检测和人类姿态估计模块 ObjDetect HummanPoseTrack
# from tasks.YOLODeepsort.YOLO_Deepsort import PedCarTrack # 行人车辆跟踪模块 PedCarTrack
# from tasks.BLIPTasks import ImgDescription
    
### ========== 聊天机器人类 ========== ###
class ChatRobot(QObject):
    # 定义信号
    response_ready = Signal(str) if HAS_PYSIDE else None  # 回复准备好时的信号
    parameters_needed = Signal(list) if HAS_PYSIDE else None  # 需要参数时的信号
    processing_task = Signal(str) if HAS_PYSIDE else None  # 处理任务时的信号
    task_completed = Signal(str, str) if HAS_PYSIDE else None  # 任务完成时的信号

    def __init__(self, chat_inter=ChatGPT(), init_message="你是一个能够进行图像识别的聊天机器人."):
        """
        可选参数：\n
        -chat_inter 与语言模型通讯的聊天接口，默认为ChatGPT
        init_message 初始化内容，默认"你是一个能够进行图像识别的聊天机器人."
        """
        if HAS_PYSIDE:
            super().__init__()
        
        self.chat_inter = chat_inter
        self.messages = [{"role": "system", "content": init_message}]
        self.task_manager = TasksManager() # 实例化一个任务管理器
        self.current_task = None  # 当前处理的任务
        self.waiting_for_params = False  # 是否等待参数
        self._RegisterTasks()

    def _RegisterTasks(self):
        """注册任务"""
        self.task_manager.register_task(
            "ObjectDetect",
            ObjDetect,
            "检测图像中的物体或人物，可以计数",
             [{"name": "image_path", "description": "图像或视频文件的路径", "required": True}, 
             {"name": "weight_path", "description": "任务使用的模型权重路径", "required": False},
             {"name": "is_show", "description": "是否需要在屏幕上显示结果", "required": False}]
        )
        self.task_manager.register_task(
            "HumanPoseEstimate", 
            HummanPoseTrack, 
            "只能估计人体姿态，不能计数",
             [{"name": "image_path", "description": "图像或视频文件的路径", "required": True}, 
             {"name": "weight_path", "description": "任务使用的模型权重路径", "required": False}, 
             {"name": "is_show", "description": "是否需要在屏幕上显示结果", "required": False}]
        )
        # self.task_manager.register_task(
        #     "PedestrianAndVehicleTracking", 
        #     PedCarTrack, 
        #     "跟踪行人和车辆",
        #      [{"name": "image_path", "description": "图像或视频文件的路径", "required": True}, 
        #      {"name": "weight_path", "description": "任务使用的模型权重路径", "required": False},
        #      {"name": "save_path", "description": "任务结果文件的存储路径", "required": False}]
        # )
        # self.task_manager.register_task(
        #     "ImageDescription", 
        #     ImgDescription, 
        #     "可以用一句话描述图像内容",
        #      [{"name": "image_path", "description": "图像文件的路径", "required": True}, 
        #      {"name": "weight_path", "description": "任务使用的模型权重路径", "required": False}]
        # )

    # 主框架
    def ChatFrame(self, question):
        """
        主处理逻辑：从用户输入到任务结果返回。\n
        输入参数，即用户的问题输入
        """
        try:
            #print(f"用户: {question}")
            self.messages.append({"role": "user", "content": question})

            # 告知 语言大模型 支持的任务的 提示模板
            task_descriptions = self.task_manager.DescribeTasks()

            # 使用 语言大模型 分析用户输入意图
            task_info = self._AnalyInput(question, task_descriptions)
            
            # 如果用户输入匹配不到任务则正常调用聊天接口
            if task_info == "General": 
                if HAS_PYSIDE:
                    self.processing_task.emit("正在思考...")
                response = self.chat_inter.StreamResponse(self.messages)
                self.messages.append({"role": "assistant", "content": response})
                if HAS_PYSIDE:
                    self.response_ready.emit(response)
                return response
                
            # 获取任务名称和参数
            task_type = task_info['task_type']
            task_params = task_info['parameters']
            
            # 检查是否缺少必要参数
            task_def = self.task_manager.GetTask(task_type)
            if not task_def:
                response = f"未知任务类型：{task_type}"
                if HAS_PYSIDE:
                    self.response_ready.emit(response)
                return response
                
            required_params = [p for p in task_def["parameters"] if p.get("required", False)]
            missing_params = []
            
            for param in required_params:
                if param["name"] not in task_params:
                    missing_params.append(param)
            
            # 如果缺少必要参数，通知GUI
            if missing_params:
                self.current_task = task_type
                self.waiting_for_params = True
                if HAS_PYSIDE:
                    self.parameters_needed.emit(required_params)
                missing_message = f"需要提供以下参数：{', '.join([p['name'] for p in missing_params])}"
                print(missing_message)
                return missing_message
                
            # 查找并执行任务
            task_callable = task_def["callable"]
            
            # 通知GUI任务开始处理
            if HAS_PYSIDE:
                self.processing_task.emit(f"正在执行{task_type}任务...")
            
            # 执行任务
            task_results = task_callable(task_params)
            
            # 通知任务已完成
            if "image_path" in task_params and HAS_PYSIDE:
                self.task_completed.emit(task_type, task_params["image_path"])
            
            # 用 GPT 根据结果生成自然语言回复
            result_summary = f"任务类型：{task_type}\n任务结果：{task_results}"
            response = self.chat_inter.StreamResponse([{"role": "user", "content": result_summary 
                                        + "\n请你根据用户的问题内容，提取或者统计以上任务执行的结果信息来回答用户的问题(全部使用中文)：\n" 
                                        + question}])
            self.messages.append({"role": "assistant", "content": response})
            if HAS_PYSIDE:
                self.response_ready.emit(response)
            return response
        except Exception as e:
            error_message = f"处理消息时发生错误: {e}"
            print(error_message)
            if HAS_PYSIDE:
                self.response_ready.emit(error_message)
            return error_message

    def _AnalyInput(self, user_input, task_descriptions):
        """
        使用 大语言模型接口 分析用户输入并提取任务信息。
        """
        template = f"""
        You're a task analysis assistant.  When a user enters a task, 
        match the most suitable task according to the following supported task types, 
        and extract the information to return: ：
        {task_descriptions}
        Only Return format:
        {{
            "task_type": <task type>,
            "parameters": <parameter dictionary>
        }}
        Hint :1. If the description of the parameter "required" is "False", there is no need to write the returned content. However, if the user enters the corresponding parameter requirements, the return information needs to be written. 
        2. If the user input does not match any of the tasks that can be performed, return the string "General". 
        3. If the user intends to perform a task, but the parameter "required" is "True" is missing, do not write this parameter in the return information
        An example of a user entering correct parameters:
            User enters: "D:\Code\ChatVision\photos\\bus.jpg", what is on this picture"
            Your answer: {{
                "task_type": "ObjectDetect",
                "parameters": {{
                "image_path": "D:\\\\Code\\\\ChatVision\\\\photos\\\\bus.jpg"  
                }}
            }}
        An example of insufficient user input parameters:
           User enters: what is on this picture
            Your answer: {{
                "task_type": "ObjectDetect",
                "parameters": {{ 
                }}
            }}
        User input is as follows: 
        {user_input}
        """
        messages = [{"role": "system", "content": "You're a task extraction assistant."},
                    {"role": "user", "content": template}]
        task_info = self.chat_inter.UnstreamResponse(messages)
        
        # print(task_info)
        if task_info == "General" : return "General"
        
        # 格式转化
        try: 
            task_info = eval(task_info)
        except Exception as e:
            print(f"返回的内容格式不正确: {e}")
            return "General"
        else:
            return task_info  # 假设 GPT 返回 Python 字典格式
    
    def set_parameters(self, parameters):
        """设置参数并继续执行任务"""
        if not self.waiting_for_params or not self.current_task:
            return False
            
        task_def = self.task_manager.GetTask(self.current_task)
        if not task_def:
            return False
            
        # 执行任务
        self.processing_task.emit(f"正在执行{self.current_task}任务...") if HAS_PYSIDE else None
        task_results = task_def["callable"](parameters)
        
        # 通知任务已完成
        if "image_path" in parameters:
            self.task_completed.emit(self.current_task, parameters["image_path"]) if HAS_PYSIDE else None
        
        # 用 GPT 根据结果生成自然语言回复
        last_question = self.messages[-1]["content"] if self.messages else ""
        result_summary = f"任务类型：{self.current_task}\n任务结果：{task_results}"
        response = self.chat_inter.StreamResponse([{"role": "user", "content": result_summary 
                                    + "\n请你根据用户的问题内容，提取或者统计以上任务执行的结果信息来回答用户的问题(全部使用中文)：\n" 
                                    + last_question}])
        
        self.messages.append({"role": "assistant", "content": response})
        self.response_ready.emit(response) if HAS_PYSIDE else None
        
        # 重置状态
        self.waiting_for_params = False
        self.current_task = None
        
        return True

    
if __name__ == '__main__':
        
    chat_robot = ChatRobot()
    
    print("开始对话（输入'退出'或'q'以结束）：")
    while True:
        user_input = input("你: ")
        if user_input.lower() == '退出' or user_input.lower() == 'q':
            break
        print("ChatIR:", end='')
        chat_robot.ChatFrame(question=user_input)
        print('')