import asyncio

async def task(id):
    await asyncio.sleep(1);
    return f"Done {id}"

async def main():
    results = await asyncio.gather(task(1), task(2))
    return results

async def task_group():
    task_list = []
    async with asyncio.TaskGroup() as tg:
        task1 = tg.create_task(task(1))
        task2 = tg.create_task(task(2))

        task_list.extend([task1, task2])

    task_results = [t.result() for t in task_list]
    return task_results



if __name__ == "__main__":
    # results = asyncio.run(main())
    results = asyncio.run(task_group())
    print(results)