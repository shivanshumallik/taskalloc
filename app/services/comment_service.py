from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, NotFoundException
from app.models.task import Task
from app.models.task_activity import TaskActivityLog
from app.models.task_comment import TaskComment
from app.models.user import Role, User
from app.schemas.task_comment import CommentCreate, CommentUpdate


async def _get_task_or_404(task_id: UUID, db: AsyncSession) -> Task:
    result = await db.execute(
        select(Task).where(Task.id == task_id, Task.is_deleted == False)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise NotFoundException("Task", str(task_id))
    return task


async def add_comment(
    task_id: UUID, data: CommentCreate, current_user: User, db: AsyncSession
) -> TaskComment:
    task = await _get_task_or_404(task_id, db)

    # Employees can only comment on their own tasks
    if current_user.role == Role.EMPLOYEE:
        if not current_user.employee_profile or task.assigned_to != current_user.employee_profile.id:
            raise ForbiddenException("Employees can only comment on their own tasks")

    comment = TaskComment(
        task_id=task_id,
        author_id=current_user.id,
        content=data.content,
    )
    db.add(comment)

    log = TaskActivityLog(
        task_id=task_id,
        actor_id=current_user.id,
        action="commented",
        new_value=data.content[:100],
    )
    db.add(log)

    await db.flush()
    await db.refresh(comment)
    return comment


async def list_comments(task_id: UUID, db: AsyncSession) -> list[TaskComment]:
    await _get_task_or_404(task_id, db)
    result = await db.execute(
        select(TaskComment)
        .where(TaskComment.task_id == task_id)
        .order_by(TaskComment.created_at.asc())
    )
    return list(result.scalars().all())


async def update_comment(
    task_id: UUID,
    comment_id: UUID,
    data: CommentUpdate,
    current_user: User,
    db: AsyncSession,
) -> TaskComment:
    await _get_task_or_404(task_id, db)
    result = await db.execute(
        select(TaskComment).where(
            TaskComment.id == comment_id, TaskComment.task_id == task_id
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise NotFoundException("Comment", str(comment_id))

    if comment.author_id != current_user.id:
        raise ForbiddenException("You can only edit your own comments")

    comment.content = data.content
    comment.is_edited = True
    await db.flush()
    return comment


async def delete_comment(
    task_id: UUID, comment_id: UUID, current_user: User, db: AsyncSession
) -> None:
    await _get_task_or_404(task_id, db)
    result = await db.execute(
        select(TaskComment).where(
            TaskComment.id == comment_id, TaskComment.task_id == task_id
        )
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise NotFoundException("Comment", str(comment_id))

    if comment.author_id != current_user.id and current_user.role != Role.ADMIN:
        raise ForbiddenException("You can only delete your own comments")

    await db.delete(comment)
