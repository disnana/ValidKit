import re
import os
import builtins
import dataclasses
from typing import Any, Callable, Dict, List, Optional, Tuple
from ._native import NATIVE_RUNTIME
from .validator import ValidationError, ErrorDetail, ValidationResult, _is_class_schema, _class_to_schema
from .v import (
    Validator,
    v,
    InstanceValidator,
    StringValidator,
    NumberValidator,
    BoolValidator,
    ListValidator,
    DictValidator,
    OneOfValidator,
)

class CompilerContext:
    def __init__(self) -> None:
        self.context: Dict[str, Any] = {
            "ValidationError": ValidationError,
            "ErrorDetail": ErrorDetail,
            "os": os,
            "re": re,
            "builtins": builtins,
        }
        self.var_counter = 0

    def add_object(self, obj: Any) -> str:
        name = f"_obj_{self.var_counter}"
        self.var_counter += 1
        self.context[name] = obj
        return name

class CompiledSchema:
    def __init__(
        self,
        schema_orig: Any,
        validate_func: Any,
        validate_collect_func: Any,
        context: CompilerContext,
        native_validator: Any = None,
    ) -> None:
        self._schema_orig = schema_orig
        self._validate_func = validate_func
        self._validate_collect_func = validate_collect_func
        self._context = context
        self._native_validator = native_validator
        self._class_builder: Optional[Callable[..., Any]] = None
        if isinstance(schema_orig, type) and _is_class_schema(schema_orig):
            if dataclasses.is_dataclass(schema_orig):
                self._class_builder = schema_orig
            elif hasattr(schema_orig, "_make") and hasattr(schema_orig, "_fields"):
                self._class_builder = schema_orig

    def validate(
        self,
        data: Any,
        partial: bool = False,
        base: Any = None,
        migrate: Optional[Dict[str, Any]] = None,
        collect_errors: bool = False,
        _force_python: bool = False,
    ) -> Any:
        # Apply migration if any (using same logic as in validator.py)
        if migrate and isinstance(data, dict):
            data = data.copy()
            for old_key, action in migrate.items():
                if old_key in data:
                    val = data.pop(old_key)
                    if isinstance(action, str):
                        data[action] = val
                    elif callable(action):
                        result_action = action(val)
                        if isinstance(result_action, tuple) and len(result_action) == 2:
                            new_key, new_val = result_action
                            data[new_key] = new_val
                        else:
                            data[old_key] = result_action

        if (
            self._native_validator is not None
            and not _force_python
            and not collect_errors
            and not partial
            and base is None
            and migrate is None
        ):
            native_result = self._native_validator.validate(data)
            if native_result is not None:
                return self._convert_class_result(native_result, partial)

        if not collect_errors and not partial and base is None:
            validated_data = self._validate_func(data, data)
            return self._convert_class_result(validated_data, partial)

        if collect_errors:
            if (
                self._native_validator is not None
                and not _force_python
                and not partial
                and base is None
                and migrate is None
            ):
                native_collect = getattr(self._native_validator, "collect", None)
                if native_collect is not None:
                    native_errors = native_collect(data)
                    if native_errors is not None:
                        errors = [
                            ErrorDetail(path, message, value)
                            for path, message, value in native_errors
                        ]
                        return ValidationResult(data, errors)

            errors: List[ErrorDetail] = []
            try:
                validated_data = self._validate_collect_func(
                    data,
                    data,
                    "",
                    errors,
                    partial,
                    base,
                )
            except ValidationError:
                validated_data = data
            return ValidationResult(validated_data, errors)

        try:
            validated_data = self._validate_func(
                data,
                data,
                "",
                False,
                None,
                partial,
                base,
            )
        except ValidationError:
            raise

        return self._convert_class_result(validated_data, partial)

    def _convert_class_result(self, validated_data: Any, partial: bool) -> Any:
        # Convert back to dataclass/NamedTuple if needed (matching validator.py)
        if not partial and self._class_builder is not None and isinstance(validated_data, dict):
            return self._class_builder(**validated_data)
        return validated_data


def _preprocess_schema(schema: Any) -> Any:
    # Resolve basic types
    if isinstance(schema, type) and schema in (str, int, float, bool):
        if schema is str:
            return v.str()
        elif schema is int:
            return v.int()
        elif schema is float:
            return v.float()
        elif schema is bool:
            return v.bool()

    # Resolve class-based schema
    if _is_class_schema(schema):
        return _class_to_schema(schema)

    # Dictionary schema: preprocess nested schemas
    if isinstance(schema, dict):
        return {k: _preprocess_schema(v) for k, v in schema.items()}

    return schema


def compile(schema: Any) -> CompiledSchema:
    schema_orig = schema
    preprocessed = _preprocess_schema(schema)
    ctx = CompilerContext()

    lines: List[str] = []
    lines.append("def validate_compiled(value, root_data, path_prefix='', collect_errors=False, errors=None, partial=False, base=None):")
    body_lines, result_var = _gen_code(preprocessed, ctx, "value", "path_prefix", "base", 4, collect_mode=False)
    lines.extend(body_lines)
    lines.append(f"    return {result_var}")

    collect_lines: List[str] = []
    collect_lines.append("def validate_compiled_collect(value, root_data, path_prefix='', errors=None, partial=False, base=None):")
    collect_lines.append("    collect_errors = True")
    collect_body_lines, collect_result_var = _gen_code(preprocessed, ctx, "value", "path_prefix", "base", 4, collect_mode=True)
    collect_lines.extend(collect_body_lines)
    collect_lines.append(f"    return {collect_result_var}")

    code_str = "\n".join(lines + [""] + collect_lines)

    # Compile the code
    local_vars: Dict[str, Any] = {}
    try:
        exec(code_str, ctx.context, local_vars)
    except Exception as e:
        raise RuntimeError(f"Failed to compile schema to Python code:\n{code_str}") from e

    validate_func = local_vars["validate_compiled"]
    validate_collect_func = local_vars["validate_compiled_collect"]
    native_validator = NATIVE_RUNTIME.compile(preprocessed)
    return CompiledSchema(schema_orig, validate_func, validate_collect_func, ctx, native_validator)


def _gen_code(
    schema: Any,
    ctx: CompilerContext,
    value_var: str,
    path_var: str,
    base_var: str,
    indent: int,
    collect_mode: bool,
) -> Tuple[List[str], str]:
    lines: List[str] = []
    indent_str = " " * indent

    if isinstance(schema, dict):
        idx = ctx.var_counter
        ctx.var_counter += 1
        dict_result_var = f"dict_res_{idx}"
        input_dict_var = f"input_dict_{idx}"
        base_dict_var = f"base_dict_{idx}"

        lines.append(f"{indent_str}if {value_var} is not None and not isinstance({value_var}, dict):")
        lines.append(f"{indent_str}    err_msg = 'Expected dict, got ' + type({value_var}).__name__")
        if collect_mode:
            lines.append(f"{indent_str}    errors.append(ErrorDetail({path_var}, err_msg, {value_var}))")
            lines.append(f"{indent_str}    {dict_result_var} = {value_var}")
        else:
            lines.append(f"{indent_str}    raise ValidationError(err_msg, {path_var}, {value_var})")

        lines.append(f"{indent_str}else:")
        lines.append(f"{indent_str}    {dict_result_var} = {{}}")
        lines.append(f"{indent_str}    {input_dict_var} = {value_var} if {value_var} is not None else {{}}")
        lines.append(f"{indent_str}    {base_dict_var} = {base_var} if isinstance({base_var}, dict) else None")

        for key, sub_schema in schema.items():
            sub_idx = ctx.var_counter
            ctx.var_counter += 1

            key_obj_name = ctx.add_object(key)
            key_path_name = ctx.add_object(str(key))
            missing_sentinel_name = ctx.add_object(object())
            current_path_var = f"current_path_{sub_idx}"
            sub_base_var = f"sub_base_{sub_idx}"
            should_validate_var = f"should_validate_{sub_idx}"

            # Setup path variable
            if path_var == "path_prefix" and indent == 4:
                lines.append(f"{indent_str}    {current_path_var} = {key_path_name}")
            else:
                lines.append(f"{indent_str}    {current_path_var} = {path_var} + '.' + {key_path_name} if {path_var} else {key_path_name}")

            # Sub-schema options validation setup
            is_optional = False
            has_default = False
            default_val = None
            env_key = None
            env_decryptor_name = None
            when_cond_name = None
            custom_error_msg = None
            secret_val = False

            if isinstance(sub_schema, Validator):
                is_optional = sub_schema._optional
                has_default = sub_schema._has_default
                default_val = sub_schema._default_value
                env_key = sub_schema._env_key
                if env_key is not None and sub_schema._env_decryptor is not None:
                    env_decryptor_name = ctx.add_object(sub_schema._env_decryptor)
                if sub_schema._when_condition is not None:
                    when_cond_name = ctx.add_object(sub_schema._when_condition)
                custom_error_msg = sub_schema._custom_error_msg
                secret_val = sub_schema._secret_val

            # Read logic if key is missing
            lines.append(f"{indent_str}    val_{sub_idx} = {input_dict_var}.get({key_obj_name}, {missing_sentinel_name})")
            lines.append(f"{indent_str}    {sub_base_var} = {base_dict_var}.get({key_obj_name}) if {base_dict_var} is not None else None")
            lines.append(f"{indent_str}    if val_{sub_idx} is not {missing_sentinel_name}:")

            sub_val_var = f"val_{sub_idx}"
            sub_lines, sub_result_var = _gen_code(sub_schema, ctx, sub_val_var, current_path_var, sub_base_var, indent + 8, collect_mode)
            lines.extend(sub_lines)

            lines.append(f"{indent_str}        {dict_result_var}[{key_obj_name}] = {sub_result_var}")

            # If missing
            lines.append(f"{indent_str}    else:")
            missing_indent = indent + 8
            m_ind = " " * missing_indent

            # 1. Environment variables
            if env_key is not None:
                lines.append(f"{m_ind}{should_validate_var} = False")
                lines.append(f"{m_ind}env_val = os.environ.get({repr(env_key)})")
                lines.append(f"{m_ind}if env_val is not None:")
                if env_decryptor_name is not None:
                    lines.append(f"{m_ind}    try:")
                    lines.append(f"{m_ind}        val_{sub_idx} = {env_decryptor_name}(env_val)")
                    lines.append(f"{m_ind}        {should_validate_var} = True")
                    lines.append(f"{m_ind}    except Exception as e:")
                    lines.append(f"{m_ind}        err_msg = 'Failed to decrypt env var: ' + str(e)")
                    if collect_mode:
                        lines.append(f"{m_ind}        errors.append(ErrorDetail({current_path_var}, err_msg, None))")
                    else:
                        lines.append(f"{m_ind}        raise ValidationError(err_msg, {current_path_var}, None)")
                else:
                    lines.append(f"{m_ind}    val_{sub_idx} = env_val")
                    lines.append(f"{m_ind}    {should_validate_var} = True")
                lines.append(f"{m_ind}else:")
                missing_indent += 4
                m_ind = " " * missing_indent

            # 2. Base value
            lines.append(f"{m_ind}if {sub_base_var} is not None:")
            lines.append(f"{m_ind}    {dict_result_var}[{key_obj_name}] = {sub_base_var}")

            # 3. Default value
            if has_default:
                default_val_name = ctx.add_object(default_val)
                lines.append(f"{m_ind}elif True:")
                lines.append(f"{m_ind}    {dict_result_var}[{key_obj_name}] = {default_val_name}")

            # 4. When condition
            elif when_cond_name is not None:
                lines.append(f"{m_ind}elif not {when_cond_name}(root_data):")
                lines.append(f"{m_ind}    pass")
                lines.append(f"{m_ind}elif {repr(is_optional)} or partial:")
                lines.append(f"{m_ind}    pass")
                lines.append(f"{m_ind}else:")
                err_msg = custom_error_msg or "Missing required key"
                err_val = "None" if not secret_val else "'***'"
                if collect_mode:
                    lines.append(f"{m_ind}    errors.append(ErrorDetail({current_path_var}, {repr(err_msg)}, {err_val}))")
                else:
                    lines.append(f"{m_ind}    raise ValidationError({repr(err_msg)}, {current_path_var}, {err_val})")

            # 5. Optional, partial, or error
            else:
                lines.append(f"{m_ind}elif {repr(is_optional)} or partial:")
                lines.append(f"{m_ind}    pass")
                lines.append(f"{m_ind}else:")
                err_msg = custom_error_msg or "Missing required key"
                err_val = "None" if not secret_val else "'***'"
                if collect_mode:
                    lines.append(f"{m_ind}    errors.append(ErrorDetail({current_path_var}, {repr(err_msg)}, {err_val}))")
                else:
                    lines.append(f"{m_ind}    raise ValidationError({repr(err_msg)}, {current_path_var}, {err_val})")

            if env_key is not None:
                missing_indent -= 4
                m_ind = " " * missing_indent

                # Environment values are the only missing-key branch that still
                # needs validation after lookup/decryption succeeds.
                lines.append(f"{m_ind}if {should_validate_var}:")

                env_sub_lines, env_sub_result_var = _gen_code(
                    sub_schema,
                    ctx,
                    sub_val_var,
                    current_path_var,
                    sub_base_var,
                    missing_indent + 4,
                    collect_mode,
                )
                lines.extend(env_sub_lines)

                lines.append(f"{m_ind}    {dict_result_var}[{key_obj_name}] = {env_sub_result_var}")

        return lines, dict_result_var

    elif isinstance(schema, Validator):
        idx = ctx.var_counter
        ctx.var_counter += 1
        res_var = f"res_{idx}"

        # Helper variables
        when_cond_name = None
        if schema._when_condition is not None:
            when_cond_name = ctx.add_object(schema._when_condition)
            lines.append(f"{indent_str}if not {when_cond_name}(root_data):")
            lines.append(f"{indent_str}    {res_var} = {base_var}")
            lines.append(f"{indent_str}else:")
            indent += 4
            indent_str = " " * indent

        if schema._optional:
            lines.append(f"{indent_str}if {value_var} is None:")
            lines.append(f"{indent_str}    {res_var} = {base_var} if {base_var} is not None else None")
            lines.append(f"{indent_str}else:")
            indent += 4
            indent_str = " " * indent

        lines.append(f"{indent_str}try:")
        try_indent = indent + 4
        try_indent_str = " " * try_indent
        handled_by_generated_code = True

        if isinstance(schema, StringValidator):
            if schema._coerce:
                lines.append(f"{try_indent_str}if not isinstance({value_var}, str):")
                lines.append(f"{try_indent_str}    {value_var} = str({value_var})")

            lines.append(f"{try_indent_str}if not isinstance({value_var}, str):")
            lines.append(f"{try_indent_str}    raise TypeError('Expected str, got ' + type({value_var}).__name__)")

            if schema._min_len is not None:
                lines.append(f"{try_indent_str}if len({value_var}) < {schema._min_len}:")
                lines.append(f"{try_indent_str}    raise ValueError('String length ' + str(len({value_var})) + ' is shorter than minimum length {schema._min_len}')")

            if schema._max_len is not None:
                lines.append(f"{try_indent_str}if len({value_var}) > {schema._max_len}:")
                lines.append(f"{try_indent_str}    raise ValueError('String length ' + str(len({value_var})) + ' is longer than maximum length {schema._max_len}')")

            if schema._regex is not None:
                regex_obj_name = ctx.add_object(schema._regex)
                lines.append(f"{try_indent_str}if not {regex_obj_name}.match({value_var}):")
                lines.append(f"{try_indent_str}    raise ValueError(\"Value '\" + str({value_var}) + \"' does not match regex '\" + {regex_obj_name}.pattern + \"'\")")

            lines.append(f"{try_indent_str}val_final_{idx} = {value_var}")

        elif isinstance(schema, NumberValidator):
            type_cls_name = "int" if schema._type_cls is int else "float"
            if schema._coerce:
                lines.append(f"{try_indent_str}if not isinstance({value_var}, {type_cls_name}):")
                lines.append(f"{try_indent_str}    try:")
                lines.append(f"{try_indent_str}        {value_var} = {type_cls_name}({value_var})")
                lines.append(f"{try_indent_str}    except (ValueError, TypeError):")
                lines.append(f"{try_indent_str}        pass")

            lines.append(f"{try_indent_str}if not isinstance({value_var}, {type_cls_name}):")
            lines.append(f"{try_indent_str}    raise TypeError('Expected {type_cls_name}, got ' + type({value_var}).__name__)")

            if schema._min is not None:
                if schema._exclusive_min:
                    lines.append(f"{try_indent_str}if {value_var} <= {schema._min}:")
                    lines.append(f"{try_indent_str}    raise ValueError('Value ' + str({value_var}) + ' must be greater than {schema._min}')")
                else:
                    lines.append(f"{try_indent_str}if {value_var} < {schema._min}:")
                    lines.append(f"{try_indent_str}    raise ValueError('Value ' + str({value_var}) + ' is less than minimum {schema._min}')")

            if schema._max is not None:
                if schema._exclusive_max:
                    lines.append(f"{try_indent_str}if {value_var} >= {schema._max}:")
                    lines.append(f"{try_indent_str}    raise ValueError('Value ' + str({value_var}) + ' must be less than {schema._max}')")
                else:
                    lines.append(f"{try_indent_str}if {value_var} > {schema._max}:")
                    lines.append(f"{try_indent_str}    raise ValueError('Value ' + str({value_var}) + ' is greater than maximum {schema._max}')")

            lines.append(f"{try_indent_str}val_final_{idx} = {value_var}")

        elif isinstance(schema, BoolValidator):
            if schema._coerce:
                lines.append(f"{try_indent_str}if not isinstance({value_var}, bool):")
                lines.append(f"{try_indent_str}    if isinstance({value_var}, str):")
                lines.append(f"{try_indent_str}        lower_val = {value_var}.lower()")
                lines.append(f"{try_indent_str}        if lower_val in ('true', '1', 'yes', 'on'):")
                lines.append(f"{try_indent_str}            {value_var} = True")
                lines.append(f"{try_indent_str}        elif lower_val in ('false', '0', 'no', 'off'):")
                lines.append(f"{try_indent_str}            {value_var} = False")
                lines.append(f"{try_indent_str}    elif isinstance({value_var}, (int, float)):")
                lines.append(f"{try_indent_str}        if {value_var} == 1:")
                lines.append(f"{try_indent_str}            {value_var} = True")
                lines.append(f"{try_indent_str}        elif {value_var} == 0:")
                lines.append(f"{try_indent_str}            {value_var} = False")

            lines.append(f"{try_indent_str}if not isinstance({value_var}, bool):")
            lines.append(f"{try_indent_str}    raise TypeError('Expected bool, got ' + type({value_var}).__name__)")
            lines.append(f"{try_indent_str}val_final_{idx} = {value_var}")

        elif isinstance(schema, ListValidator):
            lines.append(f"{try_indent_str}if not isinstance({value_var}, (list, tuple)):")
            lines.append(f"{try_indent_str}    raise TypeError('Expected list, got ' + type({value_var}).__name__)")

            if schema._min_len is not None:
                lines.append(f"{try_indent_str}if len({value_var}) < {schema._min_len}:")
                lines.append(f"{try_indent_str}    raise ValueError('List length ' + str(len({value_var})) + ' is shorter than minimum length {schema._min_len}')")

            if schema._max_len is not None:
                lines.append(f"{try_indent_str}if len({value_var}) > {schema._max_len}:")
                lines.append(f"{try_indent_str}    raise ValueError('List length ' + str(len({value_var})) + ' is longer than maximum length {schema._max_len}')")

            list_res_var = f"list_res_{idx}"
            list_index_var = f"i_list_{idx}"
            list_item_var = f"item_list_{idx}"
            list_item_path_var = f"item_path_{idx}"
            lines.append(f"{try_indent_str}{list_res_var} = []")
            lines.append(f"{try_indent_str}for {list_index_var}, {list_item_var} in enumerate({value_var}):")
            lines.append(f"{try_indent_str}    {list_item_path_var} = {path_var} + '[' + str({list_index_var}) + ']' if {path_var} else '[' + str({list_index_var}) + ']'")

            preprocessed_item = _preprocess_schema(schema._item_validator)
            item_lines, sub_res_var = _gen_code(preprocessed_item, ctx, list_item_var, list_item_path_var, "None", try_indent + 4, collect_mode)
            lines.extend(item_lines)
            lines.append(f"{try_indent_str}    {list_res_var}.append({sub_res_var})")
            lines.append(f"{try_indent_str}val_final_{idx} = {list_res_var}")

        elif isinstance(schema, DictValidator):
            key_type_name = schema._key_type.__name__
            lines.append(f"{try_indent_str}if not isinstance({value_var}, dict):")
            lines.append(f"{try_indent_str}    raise TypeError('Expected dict, got ' + type({value_var}).__name__)")

            dict_res_var = f"dict_res_{idx}"
            dict_key_var = f"k_dict_{idx}"
            dict_value_var = f"v_dict_{idx}"
            dict_item_path_var = f"dict_item_path_{idx}"
            lines.append(f"{try_indent_str}{dict_res_var} = {{}}")
            lines.append(f"{try_indent_str}for {dict_key_var}, {dict_value_var} in {value_var}.items():")
            lines.append(f"{try_indent_str}    if not isinstance({dict_key_var}, {ctx.add_object(schema._key_type)}):")
            lines.append(f"{try_indent_str}        raise TypeError('Expected key type {key_type_name}, got ' + type({dict_key_var}).__name__)")
            lines.append(f"{try_indent_str}    {dict_item_path_var} = {path_var} + '.' + str({dict_key_var}) if {path_var} else str({dict_key_var})")

            preprocessed_val = _preprocess_schema(schema._value_validator)
            val_lines, sub_res_var = _gen_code(preprocessed_val, ctx, dict_value_var, dict_item_path_var, "None", try_indent + 4, collect_mode)
            lines.extend(val_lines)
            lines.append(f"{try_indent_str}    {dict_res_var}[{dict_key_var}] = {sub_res_var}")
            lines.append(f"{try_indent_str}val_final_{idx} = {dict_res_var}")

        elif isinstance(schema, OneOfValidator):
            choices_name = ctx.add_object(schema._choices)
            lines.append(f"{try_indent_str}if {value_var} not in {choices_name}:")
            lines.append(f"{try_indent_str}    raise ValueError(\"Value '\" + str({value_var}) + \"' is not one of \" + str({choices_name}))")
            lines.append(f"{try_indent_str}val_final_{idx} = {value_var}")

        elif isinstance(schema, InstanceValidator):
            type_cls_name = ctx.add_object(schema._instance_type)
            if schema._coerce:
                lines.append(f"{try_indent_str}if not isinstance({value_var}, {type_cls_name}):")
                lines.append(f"{try_indent_str}    try:")
                lines.append(f"{try_indent_str}        {value_var} = {type_cls_name}({value_var})")
                lines.append(f"{try_indent_str}    except Exception as e:")
                lines.append(f"{try_indent_str}        raise TypeError('Expected instance of ' + {type_cls_name}.__name__ + ', got ' + type({value_var}).__name__) from e")
                lines.append(f"{try_indent_str}    if not isinstance({value_var}, {type_cls_name}):")
                lines.append(f"{try_indent_str}        raise TypeError('Expected instance of ' + {type_cls_name}.__name__ + ', got ' + type({value_var}).__name__)")
            else:
                lines.append(f"{try_indent_str}if not isinstance({value_var}, {type_cls_name}):")
                lines.append(f"{try_indent_str}    raise TypeError('Expected instance of ' + {type_cls_name}.__name__ + ', got ' + type({value_var}).__name__)")
            lines.append(f"{try_indent_str}val_final_{idx} = {value_var}")

        else:
            # Fallback to standard validation
            handled_by_generated_code = False
            validator_name = ctx.add_object(schema)
            lines.append(f"{try_indent_str}val_final_{idx} = {validator_name}.validate({value_var}, root_data, {path_var}, {repr(collect_mode)}, errors)")

        # Custom checks execution
        if handled_by_generated_code and schema._custom_checks:
            for check in schema._custom_checks:
                check_name = ctx.add_object(check)
                lines.append(f"{try_indent_str}val_final_{idx} = {check_name}(val_final_{idx})")

        lines.append(f"{try_indent_str}{res_var} = val_final_{idx}")

        # Exception handler
        lines.append(f"{indent_str}except (TypeError, ValueError) as e:")
        err_msg_expr = repr(schema._custom_error_msg) if schema._custom_error_msg else "str(e)"
        err_val_expr = "'***'" if schema._secret_val else value_var
        if collect_mode:
            lines.append(f"{indent_str}    errors.append(ErrorDetail({path_var}, {err_msg_expr}, {err_val_expr}))")
            lines.append(f"{indent_str}    {res_var} = {value_var}")
        else:
            lines.append(f"{indent_str}    raise ValidationError({err_msg_expr}, {path_var}, {err_val_expr})")

        # Close optional block
        if schema._optional:
            indent -= 4
            indent_str = " " * indent

        # Close when_condition block
        if schema._when_condition is not None:
            indent -= 4
            indent_str = " " * indent

        return lines, res_var

    else:
        # Pass-through for static values/untyped schema
        idx = ctx.var_counter
        ctx.var_counter += 1
        res_var = f"res_{idx}"
        lines.append(f"{indent_str}{res_var} = {value_var}")
        return lines, res_var
