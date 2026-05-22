
## Iteration 2
LLM: semantic reasoning (planning intents)
Backend: Deterministic logic (exact schedule)

LLM output contract:  
```json
{
  "planning_intents": [
        {
            "todo_id": "string",
            "user_priority": "1-5 or null",
            "inferred_priority": "1-5 or null",
            "preferred_time_window": "morning | afternoon | evening | flexible",
            "preferred_start": "HH:MM or null",
            "deep_work": true,
            "avoid_splitting": true,
            "reason": "string"
        }
    ]
}
```

> todo_id: 必须来自 todo_items  
> user_priority: explicitly mentioned by user. e.g. I want to do this first today   
> inferred_priority: LLM 根据用户意愿和任务性质排序，1最高  
> preferred_time_window: morning / afternoon / evening / flexible  
> preferred_start: 可选，只是 hint，不是 hard constraint  
> deep_work: 是否需要连续专注时间  
> avoid_splitting: 是否尽量不要拆开  
> reason: 给 backend/debug/README 用，可选  

LLM should NOT return:  
```json
{
  "start": "09:00",
  "end": "11:00"
}
```

Backend will do:  
> 1. 按 priority 排序  
> 2. 根据 todo_items duration_minutes 算 end time  
> 3. 避开 calendar busy blocks
> 4. 避免 task-task overlap
> 5. 如果 preferred_start 不可用，找下一个可用 slot
> 6. 输出最终 concrete plan


