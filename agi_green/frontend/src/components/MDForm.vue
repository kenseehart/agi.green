<template>
    <Vueform v-bind="vueform" />
</template>

<script>

import { Vueform } from '@vueform/vueform';
import jsYaml from 'js-yaml';
import { ref, watch } from 'vue';

export default {
    components: {
        Vueform,
    },
    props: ['yamlSchema', 'jsonSchema'],
    setup(props) {
        const vueform = ref({
            schema: {
            },
        });

        // Watchers to update schema based on props
        watch(() => props.yamlSchema, (newVal) => {
            if (newVal) {
                const content = jsYaml.load(newVal);
                content.schema.form_id = {
                    type: 'hidden',
                    default: content.id,
                };
                console.log('YAML', content);
                vueform.value.schema = content.schema;
            }
        }, { immediate: true });

        watch(() => props.jsonSchema, (newVal) => {
            if (newVal) {
                const content = JSON.parse(newVal);
                content.schema.form_id = {
                    type: 'hidden',
                    default: content.id,
                };
                console.log('JSON:', content);
                vueform.value.schema = content.schema;
            }
        }, { immediate: true });

        return { vueform };
    },
};

</script>



