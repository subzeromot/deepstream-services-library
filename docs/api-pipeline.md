# Pipeline API Refernce

## Pipeline API
* [dsl_pipeline_new](#dsl_pipeline_new)
* [dsl_pipeline_delete](#dsl_pipeline_delete)
* [dsl_pipeline_delete_many](#dsl_pipeline_delete_many)
* [dsl_pipeline_delete_all](#dsl_pipeline_delete_all)
* [dsl_pipeline_list_size](#dsl_pipeline_list_size)
* [dsl_pipeline_list_all](#dsl_pipeline_list_all)
* [dsl_pipeline_dump_to_dot](#dsl_pipeline_dump_to_dot)
* [dsl_pipeline_dump_to_dot_with_ts](#dsl_pipeline_dump_to_dot_with_ts)
* [dsl_pipeline_state_change_listener_add](#dsl_pipeline_state_change_listener_add)
* [dsl_pipeline_state_change_listener_remove](#dsl_pipeline_state_change_listener_remove)
* [dsl_pipeline_display_event_handler_add](#dsl_pipeline_display_event_handler_add)
* [dsl_pipeline_display_event_handler_remove](#dsl_pipeline_display_event_handler_remove)

## Return Values
The following return codes are used by the Pipeline API
```C++
#define DSL_RESULT_PIPELINE_RESULT                                  0x11000000
#define DSL_RESULT_PIPELINE_NAME_NOT_UNIQUE                         0x11000001
#define DSL_RESULT_PIPELINE_NAME_NOT_FOUND                          0x11000010
#define DSL_RESULT_PIPELINE_NAME_BAD_FORMAT                         0x11000011
#define DSL_RESULT_PIPELINE_STATE_PAUSED                            0x11000100
#define DSL_RESULT_PIPELINE_STATE_RUNNING                           0x11000101
#define DSL_RESULT_PIPELINE_NEW_EXCEPTION                           0x11000110
#define DSL_RESULT_PIPELINE_COMPONENT_ADD_FAILED                    0x11000111
#define DSL_RESULT_PIPELINE_STREAMMUX_SETUP_FAILED                  0x11001000
#define DSL_RESULT_PIPELINE_FAILED_TO_PLAY                          0x11001001
#define DSL_RESULT_PIPELINE_FAILED_TO_PAUSE                         0x11001010
#define DSL_RESULT_PIPELINE_LISTENER_NOT_UNIQUE                     0x11001011
#define DSL_RESULT_PIPELINE_LISTENER_NOT_FOUND                      0x11001100
#define DSL_RESULT_PIPELINE_HANDLER_NOT_UNIQUE                      0x11001101
#define DSL_RESULT_PIPELINE_HANDLER_NOT_FOUND                       0x11001110
#define DSL_RESULT_PIPELINE_SUBSCRIBER_NOT_UNIQUE                   0x11010001
#define DSL_RESULT_PIPELINE_SUBSCRIBER_NOT_FOUND                    0x11010010
```

## Constructors
### *dsl_pipeline_new*
```C++
DslReturnType dsl_pipeline_new(const char* pipeline);
```
The constructor creates a uniquely named Pipeline. Construction will fail
if the name is currently in use.

**Parameters**
* `pipeline` - unique name for the Pipeline to create.

**Returns**
`DSL_RESULT_SUCCESS` on successful creation. One of the [Return Values](#return-values) defined above on failure

## Destructors
### *dsl_pipeline_delete*
```C++
DslReturnType dsl_pipeline_delete(const char* pipeline);
```
This destructor deletes a single uniquely named Pipeline. 
All components owned by the pipeline move to a state of `not-in-use`

**Parameters**
* `pipelines` - unique name for the Pipeline to delete

**Returns**
`DSL_RESULT_SUCCESS` on successful deletion. One of the [Return Values](#return-values) defined above on failure

### *dsl_pipeline_delete_many*
```C++
DslReturnType dsl_pipeline_delete_many(const char** pipelines);
```
This destructor deletes multiple uniquely named Pipelines. All names are first checked for existence. 
The function returns DSL_RESULT_PIPELINE_NAME_NOT_FOUND on first occurrence of not found, before making any deletions. 
All components owned by the Pipelines move to a state of `not-in-use`

**Parameters**
* `pipelines` - a NULL terminated array of uniquely named Pipelines to delete.

**Returns**
`DSL_RESULT_SUCCESS` on successful deletion. One of the [Return Values](#return-values) defined above on failure

### *dsl_pipeline_delete_all*
```C++
DslReturnType dsl_pipeline_delete_all();
```
This destructor deletes all Pipelines currently in memory  All components owned by the pipelines move to a state of `not-in-use`

**Returns**
`DSL_RESULT_SUCCESS` on successful deletion. One of the [Return Values](#return-values) defined above on failure

## Methods
### *dsl_pipeline_list_size*
```C++
uint dsl_pipeline_list_size();
```
This method returns the Pipeline list size

**Returns** the number of Pipelines currently in memory

### *dsl_pipeline_list_all*
```C++
const char** dsl_pipeline_list_all();
```
This method returns the list of Pipelines currently in  memory

**Returns** a NULL terminated array of Pipeline (char*) names

### *dsl_pipeline_dump_to_dot*
```C++
DslReturnType dsl_pipeline_dump_to_dot(const char* pipeline, char* filename);
```
This method dumps a Pipeline's graph to dot file. The GStreamer Pipeline will a create 
topology graph on each change of state to ready, playing and paused if the debug 
enviornment variable `GST_DEBUG_DUMP_DOT_DIR` is set.

GStreamer will add the `.dot` suffix and write the file to the directory specified by
the environment variable. The caller of this service is responsible for providing a 
correctly formatted and unused filename. 

**Parameters**
* `pipeline` - unique name of the Pipeline to dump
* `filename` - name of the file without extension.

**Returns**  `DSL_RESULT_SUCCESS` on successful file dump. One of the [Return Values](#return-values) defined above on failure.

### *dsl_pipeline_dump_to_dot_with_ts*
```C++
DslReturnType dsl_pipeline_dump_to_dot_with_ts(const char* pipeline, char* filename);
```
This method dumps a Pipeline's graph to dot file prefixed with the current timestamp. 
Except for the prefix, this method performs the identical service as 
[dsl_pipeline_dump_to_dot](#dsl_pipeline_dump_to_dot).

### *dsl_pipeline_state_change_listener_add*
```C++
DslReturnType dsl_pipeline_state_change_listener_add(const char* pipeline, 
    state_change_listener_cb listener, void* user_data);
```
This service adds a callback function of type [dsl_state_change_listener_cb](#dsl_state_change_listener_cb) to a
pipeline identified by it's unique name. The function will be called on every Pipeline change-of-state, with 
current and previous state information and the client provided `user_data`. Multiple calback functions can be 
registered with one Pipeline, and one callback function can be registered with multiple Pipelines.


**Parameters**
* `pipeline` - unique name of the Pipeline to update.
* `listener` - state change listener callback function to add.
* `user_data` - opaque pointer to user data returned to the listner is called back

**Returns**  `DSL_RESULT_SUCCESS` on successful add. One of the [Return Values](#return-values) defined above on failure.

### *dsl_pipeline_state_change_listener_remove*
```C++
DslReturnType dsl_pipeline_state_change_listener_remove(const char* pipeline, 
    state_change_listener_cb listener);
```
This service removes a callback function of type [state_change_listener_cb](#state_change_listener_cb) from a
pipeline identified by it's unique name.


### *dsl_pipeline_display_event_handler_add*
```C++
DslReturnType dsl_pipeline_display_event_handler_add(const char* pipeline, 
    dsl_display_event_handler_cb handler, void* user_data);
```
This service adds a callback function of type [dsl_display_event_handler_cb](#dsl_display_event_handler_cb) to a
pipeline identified by it's unique name. The function will be called on every Pipeline Window/Display [KeyPressed|ButtonPressed] with event info and the client provided `user_data`. Multiple calback functions can be registered with one Pipeline, and one callback function can be registered with multiple Pipelines.

**Parameters**
* `pipeline` - unique name of the Pipeline to update.
* `handler` - window/display event handler callback function to add.
* `user_data` - opaque pointer to user data returned to the handler when called back

**Returns**  `DSL_RESULT_SUCCESS` on successful add. One of the [Return Values](#return-values) defined above on failure.


### *dsl_pipeline_display_event_handler_remove*
```C++
DslReturnType dsl_pipeline_display_event_handler_remove(const char* pipeline, 
    dsl_display_event_handler_cb handler);
```

**Parameters**
* `pipeline` - unique name of the Pipeline to update
* `handler` - display event handler callback function to remove.

**Returns**  `DSL_RESULT_SUCCESS` on successful remove. One of the [Return Values](#return-values) defined above on failure.