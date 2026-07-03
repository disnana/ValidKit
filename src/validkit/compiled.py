import re
import os
import builtins
from typing import Any, Dict, List, Optional, Union, Tuple, Type
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
    DateTimeValidator,
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
    def __init__(self, schema_orig: Any, validate_func: Any, context: CompilerContext) -> None:
        self._schema_orig = schema_orig
        self._validate_func = validate_func
        self._context = context

    def validate(
        self,
        data: Any,
        partial: bool = False,
        base: Any = None,
        migrate: Optional[Dict[str, Any]] = None,
        collect_errors: bool = False,
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

        errors: List[ErrorDetail] = []
        try:
            validated_data = self._validate_func(
                data,
                root_data=data,
                path_prefix="",
                collect_errors=collect_errors,
                errors=errors,
                partial=partial,
                base=base,
            )
        except ValidationError:
            if not collect_errors:
                raise
            validated_data = data

        if collect_errors:
            return ValidationResult(validated_data, errors)

        # Convert back to dataclass/NamedTuple if needed (matching validator.py)
        if (
            not partial
            and isinstance(self._schema_orig, type)
            and _is_class_schema(self._schema_orig)
            and isinstance(validated_data, dict)
        ):
            import dataclasses
            if dataclasses.is_dataclass(self._schema_orig):
                return self._schema_orig(**validated_data)
            if hasattr(self._schema_orig, "_make") and hasattr(self._schema_orig, "_fields"):
                return self._schema_orig(**validated_data)

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
    
    # Code generation helper
    lines = []
    lines.append("def validate_compiled(value, root_data, path_prefix='', collect_errors=False, errors=None, partial=False, base=None):")
    
    # Generate verification body
    body_lines, result_var = _gen_code(preprocessed, ctx, "value", "path_prefix", 4)
    lines.extend(body_lines)
    lines.append(f"    return {result_var}")
    
    code_str = "\n".join(lines)
    
    # Compile the code
    local_vars = {}
    try:
        exec(code_str, ctx.context, local_vars)
    except Exception as e:
        raise RuntimeError(f"Failed to compile schema to Python code:\n{code_str}") from e
        
    validate_func = local_vars["validate_compiled"]
    return CompiledSchema(schema_orig, validate_func, ctx)


def _gen_code(schema: Any, ctx: CompilerContext, value_var: str, path_var: str, indent: int) -> Tuple[List[str], str]:
    lines = []
    indent_str = " " * indent
    
    if isinstance(schema, dict):
        idx = ctx.var_counter
        ctx.var_counter += 1
        dict_result_var = f"dict_res_{idx}"
        
        lines.append(f"{indent_str}if {value_var} is not None and not isinstance({value_var}, dict):")
        lines.append(f"{indent_str}    err_msg = 'Expected dict, got ' + type({value_var}).__name__")
        lines.append(f"{indent_str}    if collect_errors and errors is not None:")
        lines.append(f"{indent_str}        errors.append(ErrorDetail({path_var}, err_msg, {value_var}))")
        lines.append(f"{indent_str}        {dict_result_var} = {value_var}")
        lines.append(f"{indent_str}    else:")
        lines.append(f"{indent_str}        raise ValidationError(err_msg, {path_var}, {value_var})")
        
        lines.append(f"{indent_str}else:")
        lines.append(f"{indent_str}    {dict_result_var} = {{}}")
        lines.append(f"{indent_str}    input_dict = {value_var} if {value_var} is not None else {{}}")
        lines.append(f"{indent_str}    base_dict = base if isinstance(base, dict) else {{}}")
        
        for key, sub_schema in schema.items():
            sub_idx = ctx.var_counter
            ctx.var_counter += 1
            
            key_obj_name = ctx.add_object(key)
            current_path_var = f"current_path_{sub_idx}"
            
            # Setup path variable
            lines.append(f"{indent_str}    {current_path_var} = {path_var} + '.' + {key_obj_name} if {path_var} else {key_obj_name}")
            
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
            lines.append(f"{indent_str}    if {key_obj_name} in input_dict:")
            lines.append(f"{indent_str}        val_{sub_idx} = input_dict[{key_obj_name}]")
            
            # If missing
            lines.append(f"{indent_str}    else:")
            missing_indent = indent + 8
            m_ind = " " * missing_indent
            
            # 1. Environment variables
            if env_key is not None:
                lines.append(f"{m_ind}env_val = os.environ.get({repr(env_key)})")
                lines.append(f"{m_ind}if env_val is not None:")
                if env_decryptor_name is not None:
                    lines.append(f"{m_ind}    try:")
                    lines.append(f"{m_ind}        val_{sub_idx} = {env_decryptor_name}(env_val)")
                    lines.append(f"{m_ind}    except Exception as e:")
                    lines.append(f"{m_ind}        err_msg = 'Failed to decrypt env var: ' + str(e)")
                    lines.append(f"{m_ind}        if collect_errors and errors is not None:")
                    lines.append(f"{m_ind}            errors.append(ErrorDetail({current_path_var}, err_msg, None))")
                    lines.append(f"{m_ind}            continue")
                    lines.append(f"{m_ind}        else:")
                    lines.append(f"{m_ind}            raise ValidationError(err_msg, {current_path_var}, None)")
                else:
                    lines.append(f"{m_ind}    val_{sub_idx} = env_val")
                lines.append(f"{m_ind}else:")
                missing_indent += 4
                m_ind = " " * missing_indent
                
            # 2. Base value
            lines.append(f"{m_ind}if {key_obj_name} in base_dict:")
            lines.append(f"{m_ind}    {dict_result_var}[{key_obj_name}] = base_dict[{key_obj_name}]")
            
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
                lines.append(f"{m_ind}    if collect_errors and errors is not None:")
                lines.append(f"{m_ind}        errors.append(ErrorDetail({current_path_var}, {repr(err_msg)}, {err_val}))")
                lines.append(f"{m_ind}    else:")
                lines.append(f"{m_ind}        raise ValidationError({repr(err_msg)}, {current_path_var}, {err_val})")
            
            # 5. Optional, partial, or error
            else:
                lines.append(f"{m_ind}elif {repr(is_optional)} or partial:")
                lines.append(f"{m_ind}    pass")
                lines.append(f"{m_ind}else:")
                err_msg = custom_error_msg or "Missing required key"
                err_val = "None" if not secret_val else "'***'"
                lines.append(f"{m_ind}    if collect_errors and errors is not None:")
                lines.append(f"{m_ind}        errors.append(ErrorDetail({current_path_var}, {repr(err_msg)}, {err_val}))")
                lines.append(f"{m_ind}    else:")
                lines.append(f"{m_ind}        raise ValidationError({repr(err_msg)}, {current_path_var}, {err_val})")
                
            if env_key is not None:
                missing_indent -= 4
                m_ind = " " * missing_indent
            
            # Run sub-validation
            lines.append(f"{indent_str}    if {key_obj_name} in input_dict or ({env_key is not None} and os.environ.get({repr(env_key)}) is not None):")
            lines.append(f"{indent_str}        try:")
            
            sub_val_var = f"val_{sub_idx}"
            sub_lines, sub_result_var = _gen_code(sub_schema, ctx, sub_val_var, current_path_var, indent + 12)
            lines.extend(sub_lines)
            
            lines.append(f"{indent_str}            {dict_result_var}[{key_obj_name}] = {sub_result_var}")
            lines.append(f"{indent_str}        except ValidationError:")
            lines.append(f"{indent_str}            if not collect_errors:")
            lines.append(f"{indent_str}                raise")
            
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
            lines.append(f"{indent_str}    {res_var} = base")
            lines.append(f"{indent_str}else:")
            indent += 4
            indent_str = " " * indent
            
        if schema._optional:
            lines.append(f"{indent_str}if {value_var} is None:")
            lines.append(f"{indent_str}    {res_var} = base if base is not None else None")
            lines.append(f"{indent_str}else:")
            indent += 4
            indent_str = " " * indent

        lines.append(f"{indent_str}try:")
        try_indent = indent + 4
        try_indent_str = " " * try_indent
        
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
                
            lines.append(f"{try_indent_str}list_res = []")
            lines.append(f"{try_indent_str}for i_list, item_list in enumerate({value_var}):")
            lines.append(f"{try_indent_str}    item_path = {path_var} + '[' + str(i_list) + ']' if {path_var} else '[' + str(i_list) + ']'")
            
            preprocessed_item = _preprocess_schema(schema._item_validator)
            item_lines, sub_res_var = _gen_code(preprocessed_item, ctx, "item_list", "item_path", try_indent + 4)
            lines.extend(item_lines)
            lines.append(f"{try_indent_str}    list_res.append({sub_res_var})")
            lines.append(f"{try_indent_str}val_final_{idx} = list_res")

        elif isinstance(schema, DictValidator):
            key_type_name = schema._key_type.__name__
            lines.append(f"{try_indent_str}if not isinstance({value_var}, dict):")
            lines.append(f"{try_indent_str}    raise TypeError('Expected dict, got ' + type({value_var}).__name__)")
            
            lines.append(f"{try_indent_str}dict_res = {{}}")
            lines.append(f"{try_indent_str}for k_dict, v_dict in {value_var}.items():")
            lines.append(f"{try_indent_str}    if not isinstance(k_dict, {ctx.add_object(schema._key_type)}):")
            lines.append(f"{try_indent_str}        raise TypeError('Expected key type {key_type_name}, got ' + type(k_dict).__name__)")
            lines.append(f"{try_indent_str}    dict_item_path = {path_var} + '.' + str(k_dict) if {path_var} else str(k_dict)")
            
            preprocessed_val = _preprocess_schema(schema._value_validator)
            val_lines, sub_res_var = _gen_code(preprocessed_val, ctx, "v_dict", "dict_item_path", try_indent + 4)
            lines.extend(val_lines)
            lines.append(f"{try_indent_str}    dict_res[k_dict] = {sub_res_var}")
            lines.append(f"{try_indent_str}val_final_{idx} = dict_res")

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
            validator_name = ctx.add_object(schema)
            lines.append(f"{try_indent_str}val_final_{idx} = {validator_name}.validate({value_var}, root_data, {path_var}, collect_errors, errors)")

        # Custom checks execution
        if schema._custom_checks:
            for check in schema._custom_checks:
                check_name = ctx.add_object(check)
                lines.append(f"{try_indent_str}val_final_{idx} = {check_name}(val_final_{idx})")
                
        lines.append(f"{try_indent_str}{res_var} = val_final_{idx}")
        
        # Exception handler
        lines.append(f"{indent_str}except (TypeError, ValueError) as e:")
        err_msg_expr = repr(schema._custom_error_msg) if schema._custom_error_msg else "str(e)"
        err_val_expr = "'***'" if schema._secret_val else value_var
        lines.append(f"{indent_str}    if collect_errors and errors is not None:")
        lines.append(f"{indent_str}        errors.append(ErrorDetail({path_var}, {err_msg_expr}, {err_val_expr}))")
        lines.append(f"{indent_str}        {res_var} = {value_var}")
        lines.append(f"{indent_str}    else:")
        lines.append(f"{indent_str}        raise ValidationError({err_msg_expr}, {path_var}, {err_val_expr})")
        
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
