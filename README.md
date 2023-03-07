# 蓝莺连接器 Lanying Connector

将蓝莺IM与其他服务连接起来，可以接收来自蓝莺IM回调服务的消息，与被连接服务如AI引擎交互，并可以将后者的回复发回到蓝莺IM。

蓝莺IM，是由[美信拓扑](https://www.lanyingim.com/)团队研发的新一代即时通讯云服务，SDK设计简单集成方便，服务采用云原生技术和多云架构，私有云也可按月付费。

当前已有模板（欢迎补充&PR）:

1. openai：通过调用[OpenAI API](https://beta.openai.com)来实现一个ChatGPT Chatbot。
2. openai-xiaolan：蓝莺IM中的小蓝AI设置，仅为演示智能客服功能用；

### 系统要求

[Python 3.7](https://www.python.org/downloads/)

### 安装与运行

1. 克隆本工程并进入工程目录
   ```bash
   $ cd lanying-connector
   ```

2. 激活虚拟环境

   ```bash
   $ python3 -m venv venv
   $ . venv/bin/activate
   ```

3. 安装依赖

   ```bash
   $ pip install -r requirements.txt
   ```

4. 复制环境变量模板文件，并进行配置

   ```bash
   $ cp .env.example .env
   ```
   其中：
   
   ```LANYING_USER_ID``` 是提供Chatbot服务的用户ID；
   
   ```LANYING_ADMIN_TOKEN``` 是蓝莺IM[管理员Token](https://console.lanyingim.com/#/home/token);
   
   ```LANYING_CONNECTOR_SERVICE``` 选择交互引擎，这里默认是 openai;
   
   ```LANYING_API_ENDPOINT``` 仅私有云需要，是应用所在API服务的地址，可从蓝莺IM控制台"应用信息"页面获取;

   ```LANYING_CONNECTOR_REDIS_SERVER``` redis的地址， 格式如：redis://:@redis:6379/0

5. 配置服务
   
   如果```LANYING_CONNECTOR_SERVICE```选择了 openai，就对应修改 configs/openai.json 对其进行配置,
   具体配置可参照[OpenAI文档](https://beta.openai.com/docs/api-reference/authentication)。

6. 运行

   ```bash
   $ flask run
   ```
   注：每次重新运行需要激活虚拟环境，别忘了操作第2步。

服务启动成功，就可以在页面上看到收发消息的基本情况了：[http://127.0.0.1:5000](http://127.0.0.1:5000)，祝玩得开心~🚀

