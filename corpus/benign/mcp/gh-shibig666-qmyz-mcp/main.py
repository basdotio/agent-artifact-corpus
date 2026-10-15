from mcp.server.fastmcp import FastMCP

import qmyz

mcp = FastMCP("QMYZ")


@mcp.tool()
async def get_courses(JSESSIONID: str) -> str:
    """获取课程名称与ID

    参数:
        JSESSIONID (str): 用户的JSESSIONID
    """
    try:
        course_dict = await qmyz.get_courses(JSESSIONID)
        return str(course_dict)
    except Exception as e:
        return f"Error fetching courses: {str(e)}"

@mcp.tool()
async def get_question(JSESSIONID: str, course_id: str) -> str:
    """获取课程题目

    参数:
        JSESSIONID (str): 用户的JSESSIONID
        course_id (str): 课程ID
    """
    try:
        question_dict = await qmyz.get_question(JSESSIONID, course_id)
        return str(question_dict)
    except Exception as e:
        return f"Error fetching question: {str(e)}"

@mcp.tool()
async def submit_question(JSESSIONID: str, course_id: str, question_id: str, answer: str) -> str:
    """提交课程题目答案, 返回答题结果。提交的answer应为选项的字母，例如 "A" 或 "B"

    参数:
        JSESSIONID (str): 用户的JSESSIONID
        course_id (str): 课程ID
        question_id (str): 题目ID
        answer (str): 答案，例如 "A" 或 "B" 等选项
    """
    try:
        result = await qmyz.submit_question(JSESSIONID, course_id, question_id, answer)
        if result:
            return "答题正确"
        else:
            return "答题错误"
    except Exception as e:
        return f"Error submitting question: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
