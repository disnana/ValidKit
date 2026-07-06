use std::collections::BTreeMap;

use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyList, PyString, PyTuple};

#[derive(Debug, Clone, PartialEq)]
pub enum Value<'a> {
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(&'a str),
    List(Vec<Value<'a>>),
    Dict(BTreeMap<&'a str, Value<'a>>),
}

#[derive(Debug, Clone, PartialEq)]
pub enum Schema {
    Any,
    Bool,
    IntPlain,
    Int {
        min: Option<f64>,
        max: Option<f64>,
    },
    IntExclusive {
        min: Option<f64>,
        max: Option<f64>,
        exclusive_min: bool,
        exclusive_max: bool,
    },
    FloatPlain,
    Float {
        min: Option<f64>,
        max: Option<f64>,
    },
    FloatExclusive {
        min: Option<f64>,
        max: Option<f64>,
        exclusive_min: bool,
        exclusive_max: bool,
    },
    Str {
        min_len: Option<usize>,
        max_len: Option<usize>,
    },
    List(Box<Schema>),
    BoundedList {
        item: Box<Schema>,
        min_len: Option<usize>,
        max_len: Option<usize>,
    },
    Dict(Box<Schema>),
    Object(Vec<Field>),
}

#[derive(Debug, Clone, PartialEq)]
pub struct Field {
    pub name: String,
    pub schema: Schema,
}

#[derive(Debug, Clone, PartialEq)]
pub struct ValidationFailure {
    pub path: String,
    pub message: String,
}

pub fn validate(schema: &Schema, value: &Value<'_>) -> Result<(), ValidationFailure> {
    validate_at(schema, value, "")
}

fn validate_at(schema: &Schema, value: &Value<'_>, path: &str) -> Result<(), ValidationFailure> {
    match schema {
        Schema::Any => Ok(()),
        Schema::Bool => match value {
            Value::Bool(_) => Ok(()),
            _ => fail(path, "Expected bool"),
        },
        Schema::IntPlain => validate_int_plain(value, path),
        Schema::Int { min, max } => validate_int(*min, *max, value, path),
        Schema::IntExclusive {
            min,
            max,
            exclusive_min,
            exclusive_max,
        } => validate_int_exclusive(*min, *max, *exclusive_min, *exclusive_max, value, path),
        Schema::FloatPlain => validate_float_plain(value, path),
        Schema::Float { min, max } => validate_float(*min, *max, value, path),
        Schema::FloatExclusive {
            min,
            max,
            exclusive_min,
            exclusive_max,
        } => validate_float_exclusive(*min, *max, *exclusive_min, *exclusive_max, value, path),
        Schema::Str { min_len, max_len } => validate_str(*min_len, *max_len, value, path),
        Schema::List(item_schema) => validate_list(item_schema, None, None, value, path),
        Schema::BoundedList {
            item,
            min_len,
            max_len,
        } => validate_list(item, *min_len, *max_len, value, path),
        Schema::Dict(value_schema) => validate_dict(value_schema, value, path),
        Schema::Object(fields) => validate_object(fields, value, path),
    }
}

fn validate_int_plain(value: &Value<'_>, path: &str) -> Result<(), ValidationFailure> {
    let number = match value {
        Value::Int(number) => number,
        _ => return fail(path, "Expected int"),
    };
    let _ = number;
    Ok(())
}

fn validate_int(
    min: Option<f64>,
    max: Option<f64>,
    value: &Value<'_>,
    path: &str,
) -> Result<(), ValidationFailure> {
    let number = match value {
        Value::Int(number) => *number,
        _ => return fail(path, "Expected int"),
    };
    let comparable = number as f64;
    if let Some(min) = min {
        if comparable < min {
            return fail(path, &format!("Value {number} is less than minimum {min}"));
        }
    }
    if let Some(max) = max {
        if comparable > max {
            return fail(
                path,
                &format!("Value {number} is greater than maximum {max}"),
            );
        }
    }
    Ok(())
}

fn validate_int_exclusive(
    min: Option<f64>,
    max: Option<f64>,
    exclusive_min: bool,
    exclusive_max: bool,
    value: &Value<'_>,
    path: &str,
) -> Result<(), ValidationFailure> {
    let number = match value {
        Value::Int(number) => *number,
        _ => return fail(path, "Expected int"),
    };
    let comparable = number as f64;
    if let Some(min) = min {
        if exclusive_min && comparable <= min {
            return fail(path, &format!("Value {number} must be greater than {min}"));
        }
        if !exclusive_min && comparable < min {
            return fail(path, &format!("Value {number} is less than minimum {min}"));
        }
    }
    if let Some(max) = max {
        if exclusive_max && comparable >= max {
            return fail(path, &format!("Value {number} must be less than {max}"));
        }
        if !exclusive_max && comparable > max {
            return fail(
                path,
                &format!("Value {number} is greater than maximum {max}"),
            );
        }
    }
    Ok(())
}

fn validate_float_plain(value: &Value<'_>, path: &str) -> Result<(), ValidationFailure> {
    match value {
        Value::Float(_) => Ok(()),
        _ => fail(path, "Expected float"),
    }
}

fn validate_float(
    min: Option<f64>,
    max: Option<f64>,
    value: &Value<'_>,
    path: &str,
) -> Result<(), ValidationFailure> {
    let number = match value {
        Value::Float(number) => *number,
        _ => return fail(path, "Expected float"),
    };

    if let Some(min) = min {
        if number < min {
            return fail(path, &format!("Value {number} is less than minimum {min}"));
        }
    }
    if let Some(max) = max {
        if number > max {
            return fail(
                path,
                &format!("Value {number} is greater than maximum {max}"),
            );
        }
    }
    Ok(())
}

fn validate_float_exclusive(
    min: Option<f64>,
    max: Option<f64>,
    exclusive_min: bool,
    exclusive_max: bool,
    value: &Value<'_>,
    path: &str,
) -> Result<(), ValidationFailure> {
    let number = match value {
        Value::Float(number) => *number,
        _ => return fail(path, "Expected float"),
    };

    if let Some(min) = min {
        if exclusive_min && number <= min {
            return fail(path, &format!("Value {number} must be greater than {min}"));
        }
        if !exclusive_min && number < min {
            return fail(path, &format!("Value {number} is less than minimum {min}"));
        }
    }
    if let Some(max) = max {
        if exclusive_max && number >= max {
            return fail(path, &format!("Value {number} must be less than {max}"));
        }
        if !exclusive_max && number > max {
            return fail(
                path,
                &format!("Value {number} is greater than maximum {max}"),
            );
        }
    }
    Ok(())
}

fn validate_str(
    min_len: Option<usize>,
    max_len: Option<usize>,
    value: &Value<'_>,
    path: &str,
) -> Result<(), ValidationFailure> {
    let text = match value {
        Value::Str(text) => *text,
        _ => return fail(path, "Expected str"),
    };

    let char_count = text.chars().count();
    if let Some(min_len) = min_len {
        if char_count < min_len {
            return fail(
                path,
                &format!("String length {char_count} is shorter than minimum length {min_len}"),
            );
        }
    }
    if let Some(max_len) = max_len {
        if char_count > max_len {
            return fail(
                path,
                &format!("String length {char_count} is longer than maximum length {max_len}"),
            );
        }
    }
    Ok(())
}

fn validate_list(
    item_schema: &Schema,
    min_len: Option<usize>,
    max_len: Option<usize>,
    value: &Value<'_>,
    path: &str,
) -> Result<(), ValidationFailure> {
    let items = match value {
        Value::List(items) => items,
        _ => return fail(path, "Expected list"),
    };

    if let Some(min_len) = min_len {
        if items.len() < min_len {
            return fail(
                path,
                &format!(
                    "List length {} is shorter than minimum length {min_len}",
                    items.len()
                ),
            );
        }
    }
    if let Some(max_len) = max_len {
        if items.len() > max_len {
            return fail(
                path,
                &format!(
                    "List length {} is longer than maximum length {max_len}",
                    items.len()
                ),
            );
        }
    }

    for (index, item) in items.iter().enumerate() {
        validate_at(item_schema, item, &list_path(path, index))?;
    }
    Ok(())
}

fn validate_dict(
    value_schema: &Schema,
    value: &Value<'_>,
    path: &str,
) -> Result<(), ValidationFailure> {
    let values = match value {
        Value::Dict(values) => values,
        _ => return fail(path, "Expected dict"),
    };

    for (key, item) in values {
        validate_at(value_schema, item, &field_path(path, key))?;
    }
    Ok(())
}

fn validate_object(
    fields: &[Field],
    value: &Value<'_>,
    path: &str,
) -> Result<(), ValidationFailure> {
    let values = match value {
        Value::Dict(values) => values,
        _ => return fail(path, "Expected dict"),
    };

    for field in fields {
        let Some(item) = values.get(field.name.as_str()) else {
            return fail(&field_path(path, &field.name), "Missing required key");
        };
        validate_at(&field.schema, item, &field_path(path, &field.name))?;
    }
    Ok(())
}

fn field_path(prefix: &str, field: &str) -> String {
    if prefix.is_empty() {
        field.to_string()
    } else {
        format!("{prefix}.{field}")
    }
}

fn list_path(prefix: &str, index: usize) -> String {
    if prefix.is_empty() {
        format!("[{index}]")
    } else {
        format!("{prefix}[{index}]")
    }
}

fn fail<T>(path: &str, message: &str) -> Result<T, ValidationFailure> {
    Err(ValidationFailure {
        path: path.to_string(),
        message: message.to_string(),
    })
}

#[pyclass]
pub struct NativeValidator {
    schema: Schema,
}

#[pymethods]
impl NativeValidator {
    fn validate(&self, _py: Python<'_>, data: Bound<'_, PyAny>) -> PyResult<Option<PyObject>> {
        if validate_python_value(&self.schema, &data)? {
            Ok(Some(data.unbind()))
        } else {
            Ok(None)
        }
    }

    fn collect(&self, py: Python<'_>, data: Bound<'_, PyAny>) -> PyResult<Option<PyObject>> {
        let errors = PyList::empty_bound(py);
        let Some(valid) = collect_python_value(py, &self.schema, &data, "", &errors)? else {
            return Ok(None);
        };
        if valid {
            Ok(Some(errors.into_any().unbind()))
        } else {
            Ok(Some(errors.into_any().unbind()))
        }
    }
}

#[pyfunction]
pub fn compile_schema(schema: Bound<'_, PyAny>) -> PyResult<Option<NativeValidator>> {
    Ok(build_schema(&schema)?.map(|schema| NativeValidator { schema }))
}

#[pymodule]
fn validkit_core(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(compile_schema, module)?)?;
    module.add_class::<NativeValidator>()?;
    Ok(())
}

fn build_schema(schema: &Bound<'_, PyAny>) -> PyResult<Option<Schema>> {
    if let Ok(dict) = schema.downcast::<PyDict>() {
        let mut fields = Vec::with_capacity(dict.len());
        for (key, value_schema) in dict.iter() {
            let Ok(name) = key.extract::<String>() else {
                return Ok(None);
            };
            let Some(schema) = build_schema(&value_schema)? else {
                return Ok(None);
            };
            fields.push(Field { name, schema });
        }
        return Ok(Some(Schema::Object(fields)));
    }

    if !is_supported_validator(schema)? {
        return Ok(None);
    }

    let type_name = schema.get_type().name()?.to_string();
    match type_name.as_str() {
        "Validator" => Ok(Some(Schema::Any)),
        "StringValidator" => build_string_schema(schema),
        "NumberValidator" => build_number_schema(schema),
        "BoolValidator" => Ok(Some(Schema::Bool)),
        "ListValidator" => {
            let item = schema.getattr("_item_validator")?;
            let Some(item_schema) = build_schema(&item)? else {
                return Ok(None);
            };
            let min_len = schema.getattr("_min_len")?.extract::<Option<usize>>()?;
            let max_len = schema.getattr("_max_len")?.extract::<Option<usize>>()?;
            if min_len.is_none() && max_len.is_none() {
                Ok(Some(Schema::List(Box::new(item_schema))))
            } else {
                Ok(Some(Schema::BoundedList {
                    item: Box::new(item_schema),
                    min_len,
                    max_len,
                }))
            }
        }
        "DictValidator" => {
            let key_type = schema.getattr("_key_type")?;
            let key_type_name = key_type.getattr("__name__")?.extract::<String>()?;
            if key_type_name != "str" {
                return Ok(None);
            }
            let value = schema.getattr("_value_validator")?;
            let Some(value_schema) = build_schema(&value)? else {
                return Ok(None);
            };
            Ok(Some(Schema::Dict(Box::new(value_schema))))
        }
        _ => Ok(None),
    }
}

fn is_supported_validator(schema: &Bound<'_, PyAny>) -> PyResult<bool> {
    if schema.getattr("_coerce")?.extract::<bool>()? {
        return Ok(false);
    }

    let custom_checks = schema.getattr("_custom_checks")?;
    if custom_checks.len()? != 0 {
        return Ok(false);
    }

    for attr in ["_when_condition", "_env_key"] {
        if !schema.getattr(attr)?.is_none() {
            return Ok(false);
        }
    }

    Ok(true)
}

fn build_string_schema(schema: &Bound<'_, PyAny>) -> PyResult<Option<Schema>> {
    if !schema.getattr("_regex")?.is_none() {
        return Ok(None);
    }

    Ok(Some(Schema::Str {
        min_len: schema.getattr("_min_len")?.extract::<Option<usize>>()?,
        max_len: schema.getattr("_max_len")?.extract::<Option<usize>>()?,
    }))
}

fn build_number_schema(schema: &Bound<'_, PyAny>) -> PyResult<Option<Schema>> {
    let type_cls = schema.getattr("_type_cls")?;
    let type_name = type_cls.getattr("__name__")?.extract::<String>()?;

    match type_name.as_str() {
        "int" => {
            let min = schema.getattr("_min")?.extract::<Option<f64>>()?;
            let max = schema.getattr("_max")?.extract::<Option<f64>>()?;
            let exclusive_min = schema.getattr("_exclusive_min")?.extract::<bool>()?;
            let exclusive_max = schema.getattr("_exclusive_max")?.extract::<bool>()?;
            if exclusive_min || exclusive_max {
                Ok(Some(Schema::IntExclusive {
                    min,
                    max,
                    exclusive_min,
                    exclusive_max,
                }))
            } else if min.is_none() && max.is_none() {
                Ok(Some(Schema::IntPlain))
            } else {
                Ok(Some(Schema::Int { min, max }))
            }
        }
        "float" => {
            let min = schema.getattr("_min")?.extract::<Option<f64>>()?;
            let max = schema.getattr("_max")?.extract::<Option<f64>>()?;
            let exclusive_min = schema.getattr("_exclusive_min")?.extract::<bool>()?;
            let exclusive_max = schema.getattr("_exclusive_max")?.extract::<bool>()?;
            if exclusive_min || exclusive_max {
                Ok(Some(Schema::FloatExclusive {
                    min,
                    max,
                    exclusive_min,
                    exclusive_max,
                }))
            } else if min.is_none() && max.is_none() {
                Ok(Some(Schema::FloatPlain))
            } else {
                Ok(Some(Schema::Float { min, max }))
            }
        }
        _ => Ok(None),
    }
}

fn validate_python_value(schema: &Schema, value: &Bound<'_, PyAny>) -> PyResult<bool> {
    match schema {
        Schema::Any => Ok(true),
        Schema::Bool => Ok(value.is_instance_of::<PyBool>()),
        Schema::IntPlain => validate_python_int_plain(value),
        Schema::Int { min, max } => validate_python_int(value, *min, *max),
        Schema::IntExclusive {
            min,
            max,
            exclusive_min,
            exclusive_max,
        } => validate_python_int_exclusive(value, *min, *max, *exclusive_min, *exclusive_max),
        Schema::FloatPlain => validate_python_float_plain(value),
        Schema::Float { min, max } => validate_python_float(value, *min, *max),
        Schema::FloatExclusive {
            min,
            max,
            exclusive_min,
            exclusive_max,
        } => validate_python_float_exclusive(value, *min, *max, *exclusive_min, *exclusive_max),
        Schema::Str { min_len, max_len } => validate_python_str(value, *min_len, *max_len),
        Schema::List(item_schema) => validate_python_list(item_schema, value),
        Schema::BoundedList {
            item,
            min_len,
            max_len,
        } => validate_python_bounded_list(item, *min_len, *max_len, value),
        Schema::Dict(value_schema) => validate_python_dict(value_schema, value),
        Schema::Object(fields) => validate_python_object(fields, value),
    }
}

fn validate_python_int_plain(value: &Bound<'_, PyAny>) -> PyResult<bool> {
    Ok(value.extract::<i64>().is_ok())
}

fn validate_python_int(
    value: &Bound<'_, PyAny>,
    min: Option<f64>,
    max: Option<f64>,
) -> PyResult<bool> {
    let Ok(number) = value.extract::<i64>() else {
        return Ok(false);
    };
    if let Some(min) = min {
        if (number as f64) < min {
            return Ok(false);
        }
    }
    if let Some(max) = max {
        if (number as f64) > max {
            return Ok(false);
        }
    }
    Ok(true)
}

fn validate_python_int_exclusive(
    value: &Bound<'_, PyAny>,
    min: Option<f64>,
    max: Option<f64>,
    exclusive_min: bool,
    exclusive_max: bool,
) -> PyResult<bool> {
    let Ok(number) = value.extract::<i64>() else {
        return Ok(false);
    };
    if let Some(min) = min {
        if exclusive_min && (number as f64) <= min {
            return Ok(false);
        }
        if !exclusive_min && (number as f64) < min {
            return Ok(false);
        }
    }
    if let Some(max) = max {
        if exclusive_max && (number as f64) >= max {
            return Ok(false);
        }
        if !exclusive_max && (number as f64) > max {
            return Ok(false);
        }
    }
    Ok(true)
}

fn validate_python_float_plain(value: &Bound<'_, PyAny>) -> PyResult<bool> {
    Ok(value.is_instance_of::<PyFloat>())
}

fn validate_python_float(
    value: &Bound<'_, PyAny>,
    min: Option<f64>,
    max: Option<f64>,
) -> PyResult<bool> {
    if !value.is_instance_of::<PyFloat>() {
        return Ok(false);
    }
    let number = value.extract::<f64>()?;
    if let Some(min) = min {
        if number < min {
            return Ok(false);
        }
    }
    if let Some(max) = max {
        if number > max {
            return Ok(false);
        }
    }
    Ok(true)
}

fn validate_python_float_exclusive(
    value: &Bound<'_, PyAny>,
    min: Option<f64>,
    max: Option<f64>,
    exclusive_min: bool,
    exclusive_max: bool,
) -> PyResult<bool> {
    if !value.is_instance_of::<PyFloat>() {
        return Ok(false);
    }
    let number = value.extract::<f64>()?;
    if let Some(min) = min {
        if exclusive_min && number <= min {
            return Ok(false);
        }
        if !exclusive_min && number < min {
            return Ok(false);
        }
    }
    if let Some(max) = max {
        if exclusive_max && number >= max {
            return Ok(false);
        }
        if !exclusive_max && number > max {
            return Ok(false);
        }
    }
    Ok(true)
}

fn validate_python_str(
    value: &Bound<'_, PyAny>,
    min_len: Option<usize>,
    max_len: Option<usize>,
) -> PyResult<bool> {
    let Ok(text_obj) = value.downcast::<PyString>() else {
        return Ok(false);
    };
    let text = text_obj.to_str()?;
    let char_count = text.chars().count();
    if let Some(min_len) = min_len {
        if char_count < min_len {
            return Ok(false);
        }
    }
    if let Some(max_len) = max_len {
        if char_count > max_len {
            return Ok(false);
        }
    }
    Ok(true)
}

fn validate_python_list(item_schema: &Schema, value: &Bound<'_, PyAny>) -> PyResult<bool> {
    if let Ok(list) = value.downcast::<PyList>() {
        for item in list.iter() {
            if !validate_python_value(item_schema, &item)? {
                return Ok(false);
            };
        }
    } else if value.downcast::<PyTuple>().is_ok() {
        return Ok(false);
    } else {
        return Ok(false);
    }
    Ok(true)
}

fn validate_python_bounded_list(
    item_schema: &Schema,
    min_len: Option<usize>,
    max_len: Option<usize>,
    value: &Bound<'_, PyAny>,
) -> PyResult<bool> {
    if let Ok(list) = value.downcast::<PyList>() {
        if let Some(min_len) = min_len {
            if list.len() < min_len {
                return Ok(false);
            }
        }
        if let Some(max_len) = max_len {
            if list.len() > max_len {
                return Ok(false);
            }
        }
        for item in list.iter() {
            if !validate_python_value(item_schema, &item)? {
                return Ok(false);
            };
        }
    } else if value.downcast::<PyTuple>().is_ok() {
        return Ok(false);
    } else {
        return Ok(false);
    }
    Ok(true)
}

fn validate_python_dict(value_schema: &Schema, value: &Bound<'_, PyAny>) -> PyResult<bool> {
    let Ok(dict) = value.downcast::<PyDict>() else {
        return Ok(false);
    };

    for (key, item) in dict.iter() {
        if !key.is_instance_of::<PyString>() {
            return Ok(false);
        }
        if !validate_python_value(value_schema, &item)? {
            return Ok(false);
        };
    }
    Ok(true)
}

fn validate_python_object(fields: &[Field], value: &Bound<'_, PyAny>) -> PyResult<bool> {
    let Ok(dict) = value.downcast::<PyDict>() else {
        return Ok(false);
    };
    if dict.len() != fields.len() {
        return Ok(false);
    }

    for field in fields {
        let Some(item) = dict.get_item(field.name.as_str())? else {
            return Ok(false);
        };
        if !validate_python_value(&field.schema, &item)? {
            return Ok(false);
        };
    }
    Ok(true)
}

fn collect_python_value(
    py: Python<'_>,
    schema: &Schema,
    value: &Bound<'_, PyAny>,
    path: &str,
    errors: &Bound<'_, PyList>,
) -> PyResult<Option<bool>> {
    match schema {
        Schema::Any => Ok(Some(true)),
        Schema::Bool => {
            if value.is_instance_of::<PyBool>() {
                Ok(Some(true))
            } else {
                push_error(py, errors, path, "Expected bool", value)?;
                Ok(Some(false))
            }
        }
        Schema::IntPlain => collect_python_int_plain(py, value, path, errors),
        Schema::Int { min, max } => collect_python_int(py, value, *min, *max, path, errors),
        Schema::IntExclusive {
            min,
            max,
            exclusive_min,
            exclusive_max,
        } => collect_python_int_exclusive(
            py,
            value,
            *min,
            *max,
            *exclusive_min,
            *exclusive_max,
            path,
            errors,
        ),
        Schema::FloatPlain => collect_python_float_plain(py, value, path, errors),
        Schema::Float { min, max } => collect_python_float(py, value, *min, *max, path, errors),
        Schema::FloatExclusive {
            min,
            max,
            exclusive_min,
            exclusive_max,
        } => collect_python_float_exclusive(
            py,
            value,
            *min,
            *max,
            *exclusive_min,
            *exclusive_max,
            path,
            errors,
        ),
        Schema::Str { min_len, max_len } => {
            collect_python_str(py, value, *min_len, *max_len, path, errors)
        }
        Schema::List(item_schema) => collect_python_list(py, item_schema, value, path, errors),
        Schema::BoundedList {
            item,
            min_len,
            max_len,
        } => collect_python_bounded_list(py, item, *min_len, *max_len, value, path, errors),
        Schema::Dict(value_schema) => collect_python_dict(py, value_schema, value, path, errors),
        Schema::Object(fields) => collect_python_object(py, fields, value, path, errors),
    }
}

fn collect_python_int_plain(
    py: Python<'_>,
    value: &Bound<'_, PyAny>,
    path: &str,
    errors: &Bound<'_, PyList>,
) -> PyResult<Option<bool>> {
    if value.extract::<i64>().is_ok() {
        Ok(Some(true))
    } else {
        push_error(py, errors, path, "Expected int", value)?;
        Ok(Some(false))
    }
}

fn collect_python_int(
    py: Python<'_>,
    value: &Bound<'_, PyAny>,
    min: Option<f64>,
    max: Option<f64>,
    path: &str,
    errors: &Bound<'_, PyList>,
) -> PyResult<Option<bool>> {
    let Ok(number) = value.extract::<i64>() else {
        push_error(py, errors, path, "Expected int", value)?;
        return Ok(Some(false));
    };
    let comparable = number as f64;
    if let Some(min) = min {
        if comparable < min {
            push_error(
                py,
                errors,
                path,
                &format!("Value {number} is less than minimum {min}"),
                value,
            )?;
            return Ok(Some(false));
        }
    }
    if let Some(max) = max {
        if comparable > max {
            push_error(
                py,
                errors,
                path,
                &format!("Value {number} is greater than maximum {max}"),
                value,
            )?;
            return Ok(Some(false));
        }
    }
    Ok(Some(true))
}

fn collect_python_int_exclusive(
    py: Python<'_>,
    value: &Bound<'_, PyAny>,
    min: Option<f64>,
    max: Option<f64>,
    exclusive_min: bool,
    exclusive_max: bool,
    path: &str,
    errors: &Bound<'_, PyList>,
) -> PyResult<Option<bool>> {
    let Ok(number) = value.extract::<i64>() else {
        push_error(py, errors, path, "Expected int", value)?;
        return Ok(Some(false));
    };
    let comparable = number as f64;
    if let Some(min) = min {
        if exclusive_min && comparable <= min {
            push_error(
                py,
                errors,
                path,
                &format!("Value {number} must be greater than {min}"),
                value,
            )?;
            return Ok(Some(false));
        }
        if !exclusive_min && comparable < min {
            push_error(
                py,
                errors,
                path,
                &format!("Value {number} is less than minimum {min}"),
                value,
            )?;
            return Ok(Some(false));
        }
    }
    if let Some(max) = max {
        if exclusive_max && comparable >= max {
            push_error(
                py,
                errors,
                path,
                &format!("Value {number} must be less than {max}"),
                value,
            )?;
            return Ok(Some(false));
        }
        if !exclusive_max && comparable > max {
            push_error(
                py,
                errors,
                path,
                &format!("Value {number} is greater than maximum {max}"),
                value,
            )?;
            return Ok(Some(false));
        }
    }
    Ok(Some(true))
}

fn collect_python_float_plain(
    py: Python<'_>,
    value: &Bound<'_, PyAny>,
    path: &str,
    errors: &Bound<'_, PyList>,
) -> PyResult<Option<bool>> {
    if value.is_instance_of::<PyFloat>() {
        Ok(Some(true))
    } else {
        push_error(py, errors, path, "Expected float", value)?;
        Ok(Some(false))
    }
}

fn collect_python_float(
    py: Python<'_>,
    value: &Bound<'_, PyAny>,
    min: Option<f64>,
    max: Option<f64>,
    path: &str,
    errors: &Bound<'_, PyList>,
) -> PyResult<Option<bool>> {
    if !value.is_instance_of::<PyFloat>() {
        push_error(py, errors, path, "Expected float", value)?;
        return Ok(Some(false));
    }
    let number = value.extract::<f64>()?;
    if let Some(min) = min {
        if number < min {
            push_error(
                py,
                errors,
                path,
                &format!("Value {number} is less than minimum {min}"),
                value,
            )?;
            return Ok(Some(false));
        }
    }
    if let Some(max) = max {
        if number > max {
            push_error(
                py,
                errors,
                path,
                &format!("Value {number} is greater than maximum {max}"),
                value,
            )?;
            return Ok(Some(false));
        }
    }
    Ok(Some(true))
}

fn collect_python_float_exclusive(
    py: Python<'_>,
    value: &Bound<'_, PyAny>,
    min: Option<f64>,
    max: Option<f64>,
    exclusive_min: bool,
    exclusive_max: bool,
    path: &str,
    errors: &Bound<'_, PyList>,
) -> PyResult<Option<bool>> {
    if !value.is_instance_of::<PyFloat>() {
        push_error(py, errors, path, "Expected float", value)?;
        return Ok(Some(false));
    }
    let number = value.extract::<f64>()?;
    if let Some(min) = min {
        if exclusive_min && number <= min {
            push_error(
                py,
                errors,
                path,
                &format!("Value {number} must be greater than {min}"),
                value,
            )?;
            return Ok(Some(false));
        }
        if !exclusive_min && number < min {
            push_error(
                py,
                errors,
                path,
                &format!("Value {number} is less than minimum {min}"),
                value,
            )?;
            return Ok(Some(false));
        }
    }
    if let Some(max) = max {
        if exclusive_max && number >= max {
            push_error(
                py,
                errors,
                path,
                &format!("Value {number} must be less than {max}"),
                value,
            )?;
            return Ok(Some(false));
        }
        if !exclusive_max && number > max {
            push_error(
                py,
                errors,
                path,
                &format!("Value {number} is greater than maximum {max}"),
                value,
            )?;
            return Ok(Some(false));
        }
    }
    Ok(Some(true))
}

fn collect_python_str(
    py: Python<'_>,
    value: &Bound<'_, PyAny>,
    min_len: Option<usize>,
    max_len: Option<usize>,
    path: &str,
    errors: &Bound<'_, PyList>,
) -> PyResult<Option<bool>> {
    let Ok(text_obj) = value.downcast::<PyString>() else {
        push_error(py, errors, path, "Expected str", value)?;
        return Ok(Some(false));
    };
    let text = text_obj.to_str()?;
    let char_count = text.chars().count();
    if let Some(min_len) = min_len {
        if char_count < min_len {
            push_error(
                py,
                errors,
                path,
                &format!("String length {char_count} is shorter than minimum length {min_len}"),
                value,
            )?;
            return Ok(Some(false));
        }
    }
    if let Some(max_len) = max_len {
        if char_count > max_len {
            push_error(
                py,
                errors,
                path,
                &format!("String length {char_count} is longer than maximum length {max_len}"),
                value,
            )?;
            return Ok(Some(false));
        }
    }
    Ok(Some(true))
}

fn collect_python_list(
    py: Python<'_>,
    item_schema: &Schema,
    value: &Bound<'_, PyAny>,
    path: &str,
    errors: &Bound<'_, PyList>,
) -> PyResult<Option<bool>> {
    let Ok(list) = value.downcast::<PyList>() else {
        if value.downcast::<PyTuple>().is_ok() {
            return Ok(None);
        }
        push_error(py, errors, path, "Expected list", value)?;
        return Ok(Some(false));
    };

    let mut valid = true;
    for (index, item) in list.iter().enumerate() {
        let item_path = format!("{path}[{index}]");
        match collect_python_value(py, item_schema, &item, &item_path, errors)? {
            Some(item_valid) => valid &= item_valid,
            None => return Ok(None),
        }
    }
    Ok(Some(valid))
}

fn collect_python_bounded_list(
    py: Python<'_>,
    item_schema: &Schema,
    min_len: Option<usize>,
    max_len: Option<usize>,
    value: &Bound<'_, PyAny>,
    path: &str,
    errors: &Bound<'_, PyList>,
) -> PyResult<Option<bool>> {
    let Ok(list) = value.downcast::<PyList>() else {
        if value.downcast::<PyTuple>().is_ok() {
            return Ok(None);
        }
        push_error(py, errors, path, "Expected list", value)?;
        return Ok(Some(false));
    };

    if let Some(min_len) = min_len {
        if list.len() < min_len {
            push_error(
                py,
                errors,
                path,
                &format!(
                    "List length {} is shorter than minimum length {min_len}",
                    list.len()
                ),
                value,
            )?;
            return Ok(Some(false));
        }
    }
    if let Some(max_len) = max_len {
        if list.len() > max_len {
            push_error(
                py,
                errors,
                path,
                &format!(
                    "List length {} is longer than maximum length {max_len}",
                    list.len()
                ),
                value,
            )?;
            return Ok(Some(false));
        }
    }

    let mut valid = true;
    for (index, item) in list.iter().enumerate() {
        let item_path = format!("{path}[{index}]");
        match collect_python_value(py, item_schema, &item, &item_path, errors)? {
            Some(item_valid) => valid &= item_valid,
            None => return Ok(None),
        }
    }
    Ok(Some(valid))
}

fn collect_python_dict(
    py: Python<'_>,
    value_schema: &Schema,
    value: &Bound<'_, PyAny>,
    path: &str,
    errors: &Bound<'_, PyList>,
) -> PyResult<Option<bool>> {
    let Ok(dict) = value.downcast::<PyDict>() else {
        push_error(py, errors, path, "Expected dict", value)?;
        return Ok(Some(false));
    };

    let mut valid = true;
    for (key, item) in dict.iter() {
        let Ok(key) = key.downcast::<PyString>() else {
            return Ok(None);
        };
        let item_path = join_path(path, key.to_str()?);
        match collect_python_value(py, value_schema, &item, &item_path, errors)? {
            Some(item_valid) => valid &= item_valid,
            None => return Ok(None),
        }
    }
    Ok(Some(valid))
}

fn collect_python_object(
    py: Python<'_>,
    fields: &[Field],
    value: &Bound<'_, PyAny>,
    path: &str,
    errors: &Bound<'_, PyList>,
) -> PyResult<Option<bool>> {
    let Ok(dict) = value.downcast::<PyDict>() else {
        push_error(py, errors, path, "Expected dict", value)?;
        return Ok(Some(false));
    };

    if dict.len() > fields.len() {
        return Ok(None);
    }

    let mut valid = true;
    if dict.len() == fields.len() {
        for field in fields {
            let Some(item) = dict.get_item(field.name.as_str())? else {
                return Ok(None);
            };
            let field_path = join_path(path, &field.name);
            match collect_python_value(py, &field.schema, &item, &field_path, errors)? {
                Some(field_valid) => valid &= field_valid,
                None => return Ok(None),
            }
        }
        return Ok(Some(valid));
    }

    let mut seen = vec![false; fields.len()];
    for (key, item) in dict.iter() {
        let Ok(key) = key.downcast::<PyString>() else {
            return Ok(None);
        };
        let name = key.to_str()?;
        let Some(index) = fields.iter().position(|field| field.name == name) else {
            return Ok(None);
        };
        seen[index] = true;
        let field_path = join_path(path, name);
        match collect_python_value(py, &fields[index].schema, &item, &field_path, errors)? {
            Some(field_valid) => valid &= field_valid,
            None => return Ok(None),
        }
    }

    for (index, field) in fields.iter().enumerate() {
        if !seen[index] {
            let field_path = join_path(path, &field.name);
            errors.append((field_path, "Missing required field", py.None()))?;
            valid = false;
        }
    }

    Ok(Some(valid))
}

fn push_error(
    _py: Python<'_>,
    errors: &Bound<'_, PyList>,
    path: &str,
    message: &str,
    value: &Bound<'_, PyAny>,
) -> PyResult<()> {
    errors.append((path, message, value))
}

fn join_path(parent: &str, child: &str) -> String {
    if parent.is_empty() {
        child.to_string()
    } else {
        format!("{parent}.{child}")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dict<'a>(items: Vec<(&'a str, Value<'a>)>) -> Value<'a> {
        Value::Dict(items.into_iter().collect())
    }

    #[test]
    fn validates_flat_object() {
        let schema = Schema::Object(vec![
            Field {
                name: "id".to_string(),
                schema: Schema::Int {
                    min: Some(1.0),
                    max: None,
                },
            },
            Field {
                name: "name".to_string(),
                schema: Schema::Str {
                    min_len: Some(3),
                    max_len: None,
                },
            },
        ]);
        let value = dict(vec![("id", Value::Int(1)), ("name", Value::Str("Alice"))]);

        assert_eq!(validate(&schema, &value), Ok(()));
    }

    #[test]
    fn reports_nested_path() {
        let schema = Schema::Object(vec![Field {
            name: "user".to_string(),
            schema: Schema::Object(vec![Field {
                name: "tags".to_string(),
                schema: Schema::List(Box::new(Schema::Str {
                    min_len: Some(2),
                    max_len: None,
                })),
            }]),
        }]);
        let value = dict(vec![(
            "user",
            dict(vec![(
                "tags",
                Value::List(vec![Value::Str("ok"), Value::Str("x")]),
            )]),
        )]);

        let failure = validate(&schema, &value).unwrap_err();
        assert_eq!(failure.path, "user.tags[1]");
        assert!(failure.message.contains("shorter than minimum length 2"));
    }

    #[test]
    fn ignores_unknown_object_keys_for_validkit_compatibility() {
        let schema = Schema::Object(vec![Field {
            name: "name".to_string(),
            schema: Schema::Str {
                min_len: None,
                max_len: None,
            },
        }]);
        let value = dict(vec![
            ("name", Value::Str("Alice")),
            ("extra", Value::Int(1)),
        ]);

        assert_eq!(validate(&schema, &value), Ok(()));
    }
}
