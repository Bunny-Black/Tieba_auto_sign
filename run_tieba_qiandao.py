from DrissionPage import ChromiumOptions, ChromiumPage
import json
import os
import shutil
import time
import requests

def read_cookie():
    """读取 cookie，优先从环境变量读取"""
    if "TIEBA_COOKIES" in os.environ:
        return json.loads(os.environ["TIEBA_COOKIES"])
    else:
        print("贴吧Cookie未配置！详细请参考教程！")
        return []

def get_level_exp(page):
    """获取等级和经验，如果找不到返回'未知'"""
    try:
        level_ele = page.ele('xpath://*[@id="pagelet_aside/pagelet/my_tieba"]/div/div[1]/div[3]/div[1]/a/div[2]').text
        level = level_ele if level_ele else "未知"
    except:
        level = "未知"
    try:
        exp_ele = page.ele('xpath://*[@id="pagelet_aside/pagelet/my_tieba"]/div/div[1]/div[3]/div[2]/a/div[2]/span[1]').text
        exp = exp_ele if exp_ele else "未知"
    except:
        exp = "未知"
    return level, exp

if __name__ == "__main__":
    print("程序开始运行")

    # 通知信息
    notice = ''


    co = ChromiumOptions().headless()
    chromium_path = shutil.which("chromium-browser")
    if chromium_path:
        co.set_browser_path(chromium_path)

    page = ChromiumPage(co)

    url = "https://tieba.baidu.com/"
    page.get(url)
    page.set.cookies(read_cookie())
    page.refresh()
    page._wait_loaded(15)


    over = False
    yeshu = 6
    count = 0

    while not over:
        yeshu += 1
        page.get(f"https://tieba.baidu.com/i/i/forum?&pn={yeshu}")
        page._wait_loaded(15)

        # 批量获取当前页所有吧链接，避免固定索引导致越界异常
        link_eles = page.eles('xpath://*[@id="like_pagelet"]/div[1]/div[1]/table/tbody/tr/td[1]/a')
        print(link_eles)
        # 如果当前页没有任何吧链接，则认为没有更多数据，结束循环
        if not link_eles:
            msg = f"全部爬取完成！本次总共签到 {count} 个吧..."
            print(msg)
            notice += msg + '\n\n'
            page.close()
            over = True
            break

        # 先快照采集链接与标题，避免后续页面跳转导致元素失效（ElementLostError）
        href_items = []
        for element in link_eles:
            try:
                url = element.attr("href")
                title = element.attr("title") or "未知吧"
                if url:
                    href_items.append((url, title))
            except Exception:
                # 元素在采集阶段失效则跳过，不影响整体
                continue

        for tieba_url, name in href_items:

            page.get(tieba_url)
            page.wait.eles_loaded('xpath://*[@id="signstar_wrapper"]/a/span[1]', timeout=30)

            # 判断是否签到
            is_sign_ele = page.ele('xpath://*[@id="signstar_wrapper"]/a/span[1]')
            is_sign = is_sign_ele.text if is_sign_ele else ""
            if is_sign.startswith("连续"):
                level, exp = get_level_exp(page)
                msg = f"{name}吧：已签到过！等级：{level}，经验：{exp}"
                print(msg)
                notice += msg + '\n\n'
                print("-------------------------------------------------")
            else:
                page.wait.eles_loaded('xpath://a[@class="j_signbtn sign_btn_bright j_cansign"]', timeout=30)
                sign_ele = page.ele('xpath://a[@class="j_signbtn sign_btn_bright j_cansign"]')
                if sign_ele:
                    # 记录签到前经验
                    level, exp_before = get_level_exp(page)

                    # 点击一次并等待结果
                    sign_ele.click()
                    time.sleep(2)
                    sign_ele.click()
                    time.sleep(2)
                    sign_ele.click()
                    time.sleep(2)

                    # 刷新并等待加载完成
                    page.refresh()
                    page._wait_loaded(15)

                    # 重新读取经验，必要时有限重试（避免元素失效与网络抖动）
                    max_retries = 3
                    retries = 0
                    level_after, exp_after = get_level_exp(page)
                    while exp_after == exp_before and retries < max_retries:
                        # 再次尝试点击（需重新获取按钮元素）
                        page.wait.eles_loaded('xpath://a[@class="j_signbtn sign_btn_bright j_cansign"]', timeout=10)
                        sign_ele_retry = page.ele('xpath://a[@class="j_signbtn sign_btn_bright j_cansign"]')
                        if not sign_ele_retry:
                            break
                        if sign_ele_retry:
                            sign_ele_retry.click()
                            time.sleep(2)  # 等待签到动作完成
                            sign_ele_retry.click()
                            time.sleep(2)  # 等待签到动作完成
                            page.refresh()

                        page._wait_loaded(15)
                        level_after, exp_after = get_level_exp(page)
                        retries += 1

                    msg = f"{name}吧：成功！等级：{level_after}，经验：{exp_before}->{exp_after}"
                    print(msg)
                    notice += msg + '\n\n'
                    print("-------------------------------------------------")
                else:
                    msg = f"错误！{name}吧：找不到签到按钮，可能页面结构变了"
                    print(msg)
                    notice += msg + '\n\n'
                    print("-------------------------------------------------")

            count += 1
            page.back()
            page._wait_loaded(10)

    if "SendKey" in os.environ:
        api = f'https://sc.ftqq.com/{os.environ["SendKey"]}.send'
        title = u"贴吧签到信息"
        data = {
        "text":title,
        "desp":notice
        }
        try:
            req = requests.post(api, data=data, timeout=60)
            if req.status_code == 200:
                print("Server酱通知发送成功")
            else:
                print(f"通知失败，状态码：{req.status_code}")
                print(api)
        except Exception as e:
            print(f"通知发送异常：{e}")
    else:
        print("未配置Server酱服务...")
