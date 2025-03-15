# 本插件为关键词语音回复(仅适用于AstrBot)

## 📑目录

- [🌟主要功能](#main-features)
- [⚙️主要命令](#main-commands)
- [📜使用事例](#main-usecases)

## <a id= "main-features">主要功能</a>

1. 关键词触发语音回复 - 当有人在群聊中提到特定关键词时，机器人会自动回复对应的本地语音文件
2. 可选文本回复 - 可以同时发送文本内容或仅发送语音
3. 灵活的匹配选项：

- 正则表达式模式
- 大小写敏感性设置
- 精确匹配选项
- 可调整的回复概率
- 可从源码调整模糊匹配的概率

## <a id= "main-commands">主要命令</a>

- /kwvoice - 为当前群组开启/关闭插件

- /文本开关 - 开启/关闭同时发送文本功能

- /kv add [关键词] [语音文件名] 

- /kv 关键词语音回复指令组

- /kv del 删除关键词

- /kv list 列出所有主关键词和子关键词

- /kv chance [] 设置回复概率 

- /kv text 设置关键词的全局文本内容（所有群组和私聊生效）

## <a id= "main-usecases">使用事例</a>
![事例](.github\img\Snipaste_2025-03-15_14-59-46.png)
![事例](.github\img\Snipaste_2025-03-15_15-01-13.png)

## 感谢DeekSeek和Cluade的大力支持（纯python小白的史山代码，提lssues轻喷QAQ）
