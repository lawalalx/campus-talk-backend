from fastapi import HTTPException
from app.db.repositories.user_repo import student_profile_repo, user_repo
from app.db.models import StudentProfile, InstitutionProfile
import cloudinary
import random
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Optional
import resend

from app.db.models import User
from app.errors import (
    UserAlreadyExists,
    InvalidCredentials,
    EmailAlreadyVerified,
    EmailNotVerified,
    UserNotFound,
    InvalidToken,
)
from app.schemas.auth import (
    UserCreateGeneralModel,
    VerificationMailSchemaResponse,
    FeedbackCreateModel,
    TokenUser,
    ResetPasswordSchemaResponseModel,
    ResetPasswordModel,
    ForgotPasswordModel, 
)
from app.core.auth import generate_passwd_hash, verify_password
from app.core.config import settings
import uuid
from app.db.models import UserRole
from app.utils.resend_email import MailService




mail_service = MailService(resend, settings)


class UserService:
    async def create_student_profile(self, student_profile_in, current_user, session):
        # Validation
        if not current_user.is_verified:
            raise HTTPException(status_code=401, detail="Email not verified. Please kindly verify your email before creating a student profile.")
        if current_user.role == UserRole.INSTITUTION:
            raise HTTPException(status_code=401, detail="Institution cannot create student profile.")
        db_user = await student_profile_repo.get_by_user_id(session, user_id=current_user.id)
        if db_user:
            raise HTTPException(status_code=400, detail="Student profile already exists.")
        if not student_profile_in.educational_level or not student_profile_in.department or not student_profile_in.matric_number:
            raise HTTPException(status_code=400, detail="Level, department, and matric number are required.")
        student_obj = StudentProfile(
            user_id=current_user.id,
            institution_id=student_profile_in.institution_id,
            institution_name=student_profile_in.institution_name,
            matric_number=student_profile_in.matric_number,
            faculty=student_profile_in.faculty,
            department=student_profile_in.department,
            educational_level=student_profile_in.educational_level,
        )
        created_student = await student_profile_repo.create(session, obj_in=student_obj)
        user = await user_repo.get_by_email(session, email=current_user.email)
        user.role = UserRole.STUDENT
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return created_student, user

    async def create_institution_profile(self, institution_profile_in, current_user, session):
        if not current_user.is_verified:
            raise HTTPException(status_code=401, detail="Email not verified. Please kindly verify your email before creating an institution profile.")
        if current_user.role == UserRole.STUDENT:
            raise HTTPException(status_code=401, detail="Student cannot create institution profile.")
        query = select(InstitutionProfile).where(InstitutionProfile.user_id == current_user.id)
        result = await session.execute(query)
        db_user = result.scalar_one_or_none()
        if db_user:
            raise HTTPException(status_code=400, detail="Institution profile already exists.")
        institution_obj_profile = InstitutionProfile(
            user_id=current_user.id,
            institution_id=institution_profile_in.institution_id,
            institution_name=institution_profile_in.institution_name,
            institution_email=institution_profile_in.institution_email
        )
        user = await user_repo.get_by_email(session, email=current_user.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        user.role = UserRole.INSTITUTION
        session.add(user)
        institution_obj_profile.profile_picture = user.profile_picture
        session.add(institution_obj_profile)
        await session.commit()
        await session.refresh(user)
        await session.refresh(institution_obj_profile)
        return institution_obj_profile, user

    async def upload_profile_picture(self, file, current_user, session):
        allowed_extensions = ["jpg", "jpeg", "png"]
        file_extension = file.filename.split(".")[-1].lower()
        if file_extension not in allowed_extensions:
            raise HTTPException(status_code=400, detail="Invalid file type. Only jpg, jpeg, and png are allowed.")
        try:
            upload_result = cloudinary.uploader.upload(
                file.file,
                folder="profile_pictures",
                public_id=f"{current_user.id}_{file.filename.split('.')[0]}"
            )
            image_url = upload_result.get("secure_url")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")
        user = await user_repo.get_by_email(session, email=current_user.email)
        user.profile_picture = image_url
        await session.commit()
        await session.refresh(user)
        return user
    async def get_user_by_email(
        self, email: str, session: AsyncSession
    ) -> Optional[User]:
        """Retrieve a user by their email address."""
        statement = select(User).where(User.email == email).options(selectinload(User.student_profile), selectinload(User.institution_profile))
        user = await session.execute(statement)
        user = user.scalar_one_or_none()
        if not user:
            print("This is the error of not finding the user")
            return None
        return user
     
    async def user_exists(self, email: str, session: AsyncSession) -> bool:
        """Check if a user with the given email already exists."""
        user = await self.get_user_by_email(email, session)
        return user is not None

    async def create_user(
        self,
        user_data: UserCreateGeneralModel,
        session: AsyncSession,
        is_google: Optional[bool] = False,
    ):
        """Create a new user in the database."""
        if await self.user_exists(user_data.email, session):
            raise UserAlreadyExists(
                message="A user with this email already exists."
            )
        # if is_google else False,
        print("The data coming in: ", user_data)

        try:
            verification_token = str(uuid.uuid4())
            hash_password = generate_passwd_hash(user_data.password)

            print("This is the verification token", verification_token)

            new_user = User(
                username=user_data.username,
                full_name=user_data.username,
                email=user_data.email,
                hashed_password=hash_password,
                is_verified=False if not is_google else True,
                verification_token=verification_token if not is_google else None,
                role=user_data.role if user_data.role else UserRole.GENERAL
            )

            session.add(new_user)
            await session.commit()

            if not is_google:
                mail_service.send_verification_email(new_user.email, str(user_data.full_name), verification_token)
            print("The new user is: ", new_user)
            return new_user

        except Exception as e:
            await session.rollback()
            raise e


    async def verify_token(self, token: str, session: AsyncSession) -> User:
        """Verify the token and retrieve the associated user."""
        if token is None:
          raise InvalidToken(
              message="The token is invalid. Please try again."
          )
        
        result = await session.execute(
            select(User).where(User.verification_token == token).options(selectinload(User.student_profile), selectinload(User.institution_profile))
        )

        user = result.scalars().first()
        if not user:
            raise UserNotFound(
                message="The user with this token does not exist"
            )
        return user



    async def authenticate_user(
        self, email: str, password: str, session: AsyncSession
    ) -> User:
        """Authenticate a user by email and password."""
        user = await self.get_user_by_email(email, session)
        if user is None:
            print("The user is not found")
            raise UserNotFound(
                message="The user with this email does not exist"
            )
        if not verify_password(password, user.password):
            print("The password is not correct")
            raise InvalidCredentials(
                message="The email or password is not correct"
            )
        if not user.is_verified:
            raise EmailNotVerified(
                message="The email is not verified"
            )
        await session.refresh(user)
        return user

    async def update_user(
        self, user: User, user_data: dict, session: AsyncSession
    ) -> User:
        """Update a user's information in the database."""
        for k, v in user_data.items():
            setattr(user, k, v)
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    # reset password
    async def forgot_password(
        self, email: ForgotPasswordModel, session: AsyncSession
    ) -> ResetPasswordSchemaResponseModel:
        """Initiate a password reset process by sending an email with a reset link."""
        user = await self.get_user_by_email(email.email, session)
        if not user:
            raise InvalidCredentials(
                message="The email or password is not correct."
            )

        # Generate and assign a new reset token
        reset_token = f"{random.randint(1000, 9999)}"
        user.verification_token = reset_token

        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Send the reset password email
        mail_service.send_reset_password_email(user.email, user.full_name, reset_token)

        return ResetPasswordSchemaResponseModel(
            status=True, message="A password reset link has been sent to your email."
        )

    async def reset_password(
        self, user: User, payload: ResetPasswordModel, session: AsyncSession
    ) -> ResetPasswordSchemaResponseModel:
        """Reset the user's password"""
        # Update the user's password
        user.password = generate_passwd_hash(payload.password)
        user.verification_token = None
        session.add(user)
        await session.commit()
        await session.refresh(user)

        return ResetPasswordSchemaResponseModel(
            status=True, message="Password reset successfully."
        )

    async def delete_user(self, user: TokenUser, session: AsyncSession, is_admin: Optional[bool] = False) -> None:
        """Delete a user from the database."""
        statement = select(User).where(User.id == user.id)
        result = await session.execute(statement)
        db_user = result.scalar_one_or_none()

        if db_user:
            await session.delete(db_user)
            await session.commit()
            return None
        else:
            raise UserNotFound(
                message="User not found"
            )

    # resend verification email
    async def resend_verification_email(
        self, email: str, session: AsyncSession
    ) -> VerificationMailSchemaResponse:
        """Resend the verification email to the user."""
        try:
            user = await self.get_user_by_email(email, session)
            if user is None:
                raise UserNotFound(
                    message="The user with this email does not exist"
                )
            if user:
                if user.is_verified:
                    raise EmailAlreadyVerified(
                        message="The email is already verified."
                    )
                verification_token = f"{random.randint(1000, 9999)}"
                user.verification_token = verification_token
                session.add(user)
                await session.commit()
                mail_service.send_verification_email(user.email, user.full_name, verification_token)

            return VerificationMailSchemaResponse(
                status=True,
                message="Verification email sent successfully",
                verification_token=verification_token,
            )
        except Exception as e:
            await session.rollback()
            raise e
